import json
import tempfile
import unittest
from pathlib import Path

from ordermind import webapp


class ReleaseEngineeringTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_desktop_package_declares_signing_and_update_hooks(self):
        package_config = json.loads((self.root / "package.json").read_text(encoding="utf-8"))
        scripts = package_config["scripts"]
        build = package_config["build"]

        self.assertIn("electron-updater", package_config["dependencies"])
        self.assertIn("release:check-signing", scripts)
        self.assertIn("release:manifest", scripts)
        self.assertEqual(build["publish"]["provider"], "generic")
        self.assertIn("ORDERMIND_UPDATE_BASE_URL", build["publish"]["url"])
        self.assertEqual(build["afterSign"], "scripts/notarize_mac.cjs")
        self.assertEqual(build["win"]["signtoolOptions"]["sign"], "scripts/sign_windows.cjs")
        self.assertEqual(build["mac"]["hardenedRuntime"], True)
        self.assertEqual(build["mac"]["gatekeeperAssess"], False)

    def test_release_scripts_are_present(self):
        required_paths = [
            "scripts/check_signing_environment.py",
            "scripts/generate_update_manifest.py",
            "scripts/notarize_mac.cjs",
            "scripts/sign_windows.cjs",
            "docs/signing-and-updates.md",
        ]
        for path in required_paths:
            with self.subTest(path=path):
                self.assertTrue((self.root / path).exists())

    def test_desktop_main_contains_update_download_flow(self):
        desktop_main = (self.root / "desktop" / "main.cjs").read_text(encoding="utf-8")

        for snippet in ("checkForUpdates", "update-available", "downloadUpdate", "update-downloaded", "quitAndInstall"):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, desktop_main)

    def test_web_update_status_reads_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = Path(tmpdir) / "update-manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "version": "0.2.0",
                        "notes": "规则模板和更新检查",
                        "pub_date": "2026-07-06T00:00:00Z",
                        "platforms": {
                            "darwin-aarch64": {
                                "url": "https://updates.example.com/OrderMind_0.2.0_mac_arm64.zip",
                                "sha256": "abc123",
                                "size": 123,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            status = webapp.check_update_status(str(manifest), current_version="0.1.0")

        self.assertEqual(status["state"], "available")
        self.assertEqual(status["latest_version"], "0.2.0")
        self.assertIn("OrderMind_0.2.0_mac_arm64.zip", status["url"])

    def test_web_update_status_handles_missing_source(self):
        status = webapp.check_update_status("", current_version="0.1.0")

        self.assertEqual(status["state"], "not_configured")
