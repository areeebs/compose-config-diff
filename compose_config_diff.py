#!/usr/bin/env python3
"""Compare canonical Docker Compose models while redacting secret-like fields."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


VERSION = "0.1.0"
SECRET_KEY = re.compile(r"(password|passwd|secret|token|api[_-]?key|private[_-]?key)", re.I)
REDACTED = "[REDACTED]"


@dataclass(frozen=True)
class Change:
    path: str
    kind: str
    before: Any
    after: Any


def sanitize(value: Any, parent_key: str = "") -> Any:
    """Redact sensitive-looking fields recursively before generating a diff."""
    if parent_key and SECRET_KEY.search(parent_key):
        return REDACTED if value is not None else None
    if isinstance(value, dict):
        return {key: sanitize(child, str(key)) for key, child in value.items()}
    if isinstance(value, list):
        return [sanitize(child, parent_key) for child in value]
    return value


def escape_path(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def compare(before: Any, after: Any, path: str = "") -> list[Change]:
    changes: list[Change] = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            child_path = f"{path}/{escape_path(str(key))}"
            if key not in before:
                changes.append(Change(child_path, "added", None, after[key]))
            elif key not in after:
                changes.append(Change(child_path, "removed", before[key], None))
            else:
                changes.extend(compare(before[key], after[key], child_path))
        return changes
    if isinstance(before, list) and isinstance(after, list):
        common = min(len(before), len(after))
        for index in range(common):
            changes.extend(compare(before[index], after[index], f"{path}/{index}"))
        for index in range(common, len(before)):
            changes.append(Change(f"{path}/{index}", "removed", before[index], None))
        for index in range(common, len(after)):
            changes.append(Change(f"{path}/{index}", "added", None, after[index]))
        return changes
    if before != after:
        changes.append(Change(path or "/", "changed", before, after))
    return changes


def load_model(files: list[Path]) -> dict[str, Any]:
    if not shutil.which("docker"):
        raise RuntimeError("Docker CLI was not found. Install Docker Desktop or Docker Engine with the Compose plugin.")
    command = ["docker", "compose"]
    for file in files:
        if not file.is_file():
            raise RuntimeError(f"Compose file not found: {file}")
        command.extend(["-f", str(file)])
    command.extend(["config", "--format", "json", "--no-interpolate", "--no-env-resolution"])
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("Docker Compose did not finish rendering a configuration within 30 seconds.") from error
    except OSError as error:
        raise RuntimeError("Could not start the Docker CLI.") from error
    if result.returncode != 0:
        raise RuntimeError("Docker Compose could not render a configuration. Run `docker compose config` yourself to inspect the error locally.")
    try:
        model = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("Docker Compose returned data that was not valid JSON. Update the Compose plugin and try again.") from error
    if not isinstance(model, dict):
        raise RuntimeError("Docker Compose returned an unexpected configuration shape.")
    return model


def display(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def render_text(changes: list[Change], before_files: list[Path], after_files: list[Path]) -> str:
    lines = [f"Compose Config Diff {VERSION}"]
    lines.append(f"Before: {', '.join(file.name for file in before_files)}")
    lines.append(f"After:  {', '.join(file.name for file in after_files)}")
    if not changes:
        lines.extend(["", "No differences found in the canonical Compose models."])
        return "\n".join(lines)
    for change in changes:
        lines.extend([
            "",
            f"{change.kind.upper()} {change.path}",
            f"  before: {display(change.before)}",
            f"  after:  {display(change.after)}",
        ])
    lines.extend(["", f"{len(changes)} difference(s). Secret-like keys are redacted; review the source files locally for context."])
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two Docker Compose configurations without starting containers.",
        epilog="Example: python3 compose_config_diff.py --before compose.yaml --after compose.prod.yaml",
    )
    parser.add_argument("--before", action="append", type=Path, required=True, help="Earlier Compose file; repeat to merge overlays")
    parser.add_argument("--after", action="append", type=Path, required=True, help="Later Compose file; repeat to merge overlays")
    parser.add_argument("--json", action="store_true", help="Print machine-readable changes with secret-like values redacted")
    parser.add_argument("--version", action="version", version=f"Compose Config Diff {VERSION}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        before_model = sanitize(load_model(args.before))
        after_model = sanitize(load_model(args.after))
    except RuntimeError as error:
        if args.json:
            print(json.dumps({"error": str(error), "changes": []}))
        else:
            print(f"Error: {error}", file=sys.stderr)
        return 2

    changes = compare(before_model, after_model)
    if args.json:
        print(json.dumps({
            "version": VERSION,
            "before_files": [file.name for file in args.before],
            "after_files": [file.name for file in args.after],
            "changes": [asdict(change) for change in changes],
        }, indent=2))
    else:
        print(render_text(changes, args.before, args.after))
    return 1 if changes else 0


if __name__ == "__main__":
    raise SystemExit(main())
