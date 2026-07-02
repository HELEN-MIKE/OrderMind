import json
import unittest
from pathlib import Path

from scripts.release_check import validate_release_readiness


class ReleaseMetadataTest(unittest.TestCase):
    def test_release_metadata_is_present_and_consistent(self):
        root = Path(__file__).resolve().parents[1]

        errors = validate_release_readiness(root)
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
        manifest = json.loads(
            (root / "release" / "update-manifest.example.json").read_text(encoding="utf-8")
        )

        self.assertEqual(errors, [])
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertEqual(manifest["version"], version)
        self.assertIn("platforms", manifest)
        self.assertIn("darwin-aarch64", manifest["platforms"])
        self.assertIn("windows-x86_64", manifest["platforms"])


if __name__ == "__main__":
    unittest.main()
