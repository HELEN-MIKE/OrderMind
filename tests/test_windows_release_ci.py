import json
import unittest
from pathlib import Path


class WindowsReleaseCiTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_desktop_sidecar_script_uses_cross_platform_python_launcher(self):
        package_config = json.loads((self.root / "package.json").read_text(encoding="utf-8"))
        scripts = package_config.get("scripts", {})

        self.assertIn("desktop:sidecar", scripts)
        self.assertEqual(
            scripts["desktop:sidecar"],
            "node scripts/run_python.cjs scripts/build_desktop_sidecar.py",
        )
        self.assertTrue((self.root / "scripts" / "run_python.cjs").exists())

    def test_desktop_builder_scripts_are_windows_shell_safe(self):
        package_config = json.loads((self.root / "package.json").read_text(encoding="utf-8"))
        scripts = package_config.get("scripts", {})

        for script_name, command in scripts.items():
            with self.subTest(script=script_name):
                self.assertNotIn("ELECTRON_MIRROR=", command)

        for script_name in ("desktop:package", "desktop:dist:mac", "desktop:dist:win", "desktop:dist"):
            with self.subTest(script=script_name):
                self.assertIn("node scripts/run_electron_builder.cjs", scripts[script_name])
        self.assertTrue((self.root / "scripts" / "run_electron_builder.cjs").exists())

    def test_github_actions_builds_windows_installers(self):
        workflow_path = self.root / ".github" / "workflows" / "release-build.yml"
        self.assertTrue(workflow_path.exists())

        workflow = workflow_path.read_text(encoding="utf-8")
        required_snippets = [
            "windows-latest",
            "npm run desktop:dist:win",
            "python -m unittest discover -s tests -v",
            "python scripts/release_check.py",
            "actions/upload-artifact",
            "OrderMind-windows-installers",
        ]
        for snippet in required_snippets:
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, workflow)


if __name__ == "__main__":
    unittest.main()
