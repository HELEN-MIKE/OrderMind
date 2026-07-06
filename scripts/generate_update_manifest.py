"""生成 OrderMind 自动更新清单。

该清单供应用内“检查更新”和后续自动更新服务使用。它不替代
electron-builder 生成的 `latest.yml`，而是提供一个跨平台、可读、可审计的
发布索引，方便早期客户试用阶段做手动升级提醒。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path


PLATFORM_BY_FRAGMENT = {
    "mac_arm64": "darwin-aarch64",
    "mac_x64": "darwin-x86_64",
    "win_x64": "windows-x86_64",
    "windows_x64": "windows-x86_64",
}


def build_update_manifest(root: Path, base_url: str, version: str, notes: str) -> dict[str, object]:
    """根据安装包目录生成更新清单。"""

    installers_dir = root / "release" / "installers"
    platforms: dict[str, dict[str, object]] = {}
    if installers_dir.exists():
        for artifact in sorted(installers_dir.iterdir()):
            if not artifact.is_file() or artifact.suffix.lower() not in {".zip", ".dmg", ".exe", ".msi"}:
                continue
            platform_name = _platform_for_artifact(artifact.name)
            if not platform_name:
                continue
            platforms[platform_name] = {
                "url": f"{base_url.rstrip('/')}/{artifact.name}",
                "sha256": _sha256(artifact),
                "size": artifact.stat().st_size,
            }
    return {
        "version": version,
        "notes": notes,
        "pub_date": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "platforms": platforms,
    }


def _platform_for_artifact(filename: str) -> str:
    normalized = filename.lower().replace("-", "_")
    for fragment, platform_name in PLATFORM_BY_FRAGMENT.items():
        if fragment in normalized:
            return platform_name
    if filename.lower().endswith((".exe", ".msi")):
        return "windows-x86_64"
    return ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_base_url = os.environ.get("ORDERMIND_UPDATE_BASE_URL") or "https://example.com/ordermind/releases"
    parser = argparse.ArgumentParser(description="Generate OrderMind update manifest")
    parser.add_argument("--base-url", default=default_base_url)
    parser.add_argument("--version", default=(root / "VERSION").read_text(encoding="utf-8").strip())
    parser.add_argument("--notes", default="OrderMind release")
    parser.add_argument("--out", default=str(root / "release" / "update-manifest.generated.json"))
    args = parser.parse_args()

    manifest = build_update_manifest(root, args.base_url, args.version, args.notes)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Update manifest written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
