import unittest

import compose_config_diff


class ComposeConfigDiffTests(unittest.TestCase):
    def test_sanitize_redacts_secret_keys_recursively(self):
        model = {
            "environment": {"API_TOKEN": "secret-value"},
            "items": [{"private_key": "another-secret"}],
            "ordinary": "kept",
        }
        sanitized = compose_config_diff.sanitize(model)
        self.assertEqual(sanitized["environment"]["API_TOKEN"], compose_config_diff.REDACTED)
        self.assertEqual(sanitized["items"][0]["private_key"], compose_config_diff.REDACTED)
        self.assertEqual(sanitized["ordinary"], "kept")

    def test_compare_escapes_json_pointer_path_parts(self):
        changes = compose_config_diff.compare({"a/b~c": 1}, {"a/b~c": 2})
        self.assertEqual(changes[0].path, "/a~1b~0c")
        self.assertEqual(changes[0].kind, "changed")

    def test_compare_tracks_list_changes_by_position(self):
        changes = compose_config_diff.compare(["old", "same"], ["new", "same", "extra"])
        self.assertEqual([(item.path, item.kind) for item in changes], [("/0", "changed"), ("/2", "added")])


if __name__ == "__main__":
    unittest.main()
