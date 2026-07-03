"""Build the Python backend executable used by the desktop shell."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIDECAR_DIR = ROOT / "release" / "desktop-sidecar"
BACKEND_NAME = "ordermind-backend.exe" if platform.system() == "Windows" else "ordermind-backend"


def main() -> int:
    pyinstaller = _find_pyinstaller()
    if not pyinstaller:
        print(
            "ERROR: PyInstaller is not installed. Run "
            "`python3 -m venv .venv-build && .venv-build/bin/python -m pip install pyinstaller==6.21.0`."
        )
        return 1

    SIDECAR_DIR.mkdir(parents=True, exist_ok=True)
    command = [
        pyinstaller,
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        Path(BACKEND_NAME).stem,
        "--distpath",
        str(SIDECAR_DIR),
        "--workpath",
        str(ROOT / "build" / "pyinstaller"),
        "--specpath",
        str(ROOT / "build" / "pyinstaller"),
        str(ROOT / "run_app.py"),
    ]
    env = {**os.environ, "PYINSTALLER_CONFIG_DIR": str(ROOT / "build" / "pyinstaller-cache")}
    subprocess.run(command, cwd=ROOT, env=env, check=True)

    produced = SIDECAR_DIR / Path(BACKEND_NAME).stem
    target = SIDECAR_DIR / BACKEND_NAME
    if produced.exists() and produced != target:
        produced.replace(target)
    if not target.exists():
        print(f"ERROR: expected sidecar was not created: {target}")
        return 1

    print(f"Desktop sidecar ready: {target}")
    return 0


def _find_pyinstaller() -> str | None:
    venv_executable = (
        ROOT
        / ".venv-build"
        / ("Scripts" if platform.system() == "Windows" else "bin")
        / ("pyinstaller.exe" if platform.system() == "Windows" else "pyinstaller")
    )
    if venv_executable.exists():
        return str(venv_executable)
    return shutil.which("pyinstaller")


if __name__ == "__main__":
    raise SystemExit(main())
