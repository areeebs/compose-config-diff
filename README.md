# Compose Config Diff

Compare two Docker Compose configurations in a readable way. The tool uses Docker Compose to normalize each model, compares the resulting structures, and redacts values under secret-like keys before printing a diff.

> **Status:** Early learning project (v0.1.0). The diff is structural and intended to help people review configuration changes. It is not a policy engine or a security audit.

## Verification

The documented before/after example has been run with Docker Compose v5.6.1 and produced seven expected differences. Unit checks cover recursive secret redaction, escaped JSON Pointer paths, and list-position comparisons. Run them with:

```sh
python3 -m unittest discover -s tests -v
```

## What it does

- Compares two Compose files or two ordered sets of base and override files.
- Shows added, removed, or changed fields by JSON Pointer-style path.
- Redacts values under keys such as `password`, `token`, and `api_key`.
- Supports human-readable and JSON output.
- Does not build, start, stop, or remove containers.

## Requirements

- Python 3.10 or newer
- Docker CLI with the Docker Compose plugin

## Compare files

From this repository:

```sh
python3 compose_config_diff.py \
  --before examples/before/compose.yaml \
  --after examples/after/compose.yaml
```

Compare overlays in order:

```sh
python3 compose_config_diff.py \
  --before examples/before/compose.yaml \
  --before examples/before/compose.override.yaml \
  --after examples/after/compose.yaml \
  --after examples/after/compose.override.yaml
```

The bundled override examples set `review-tier` to `local` before the change and `staging` after it.

For machine-readable output:

```sh
python3 compose_config_diff.py \
  --before examples/before/compose.yaml \
  --after examples/after/compose.yaml \
  --json
```

Exit codes: `0` means the models match, `1` means differences were found, and `2` means a configuration could not be rendered.

## Secret handling

Compose renders canonical JSON with interpolation and `.env` resolution disabled. The tool then replaces values under secret-like keys before creating the diff. It does not print Compose error output because that output can contain user-provided configuration text. This is a safety measure, not a guarantee that every possible secret is recognized. Review files locally before sharing diff output.

Docker documents canonical JSON output and the no-interpolation options in [`docker compose config`](https://docs.docker.com/reference/cli/docker/compose/config/).

## Example

Compare the files in `examples/before` and `examples/after`. Notice that the before and after samples use fake values, and secret-like values are redacted in output.

## Limits

Lists are compared by position, which can make reordered list entries appear as changes. The tool does not determine whether a configuration change is safe or intentional. A clean diff means the rendered models are structurally equal after secret-key redaction; it does not prove that two deployments behave the same.

## Contributing

Clear examples, better path explanations, and improvements to redaction are welcome. Use fake values in examples and never commit real credentials or private configuration. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
