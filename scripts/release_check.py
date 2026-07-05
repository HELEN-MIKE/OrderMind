"""发布前检查脚本。

这个脚本不负责真正打包，而是检查每个版本发布前必须存在的元数据。
这样可以避免“代码能跑，但没有版本号、变更日志、升级清单”的交付问题。
"""

from __future__ import annotations

import json
import re
from pathlib import Path


VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def validate_release_readiness(root: Path) -> list[str]:
    """检查发布所需的版本号、变更日志和升级清单。"""

    errors: list[str] = []
    version_path = root / "VERSION"
    changelog_path = root / "CHANGELOG.md"
    manifest_path = root / "release" / "update-manifest.example.json"
    desktop_main_path = root / "desktop" / "main.cjs"
    desktop_package_path = root / "package.json"
    desktop_sidecar_script_path = root / "scripts" / "build_desktop_sidecar.py"
    desktop_icon_script_path = root / "scripts" / "generate_desktop_icons.py"
    mac_icon_path = root / "desktop" / "resources" / "icon.icns"
    windows_icon_path = root / "desktop" / "resources" / "icon.ico"
    sample_order_dir = root / "samples" / "customer_like_orders"
    sample_pdf_path = sample_order_dir / "text_pdf_order.pdf"

    if not version_path.exists():
        errors.append("VERSION 文件缺失")
        return errors

    version = version_path.read_text(encoding="utf-8").strip()
    if not VERSION_RE.match(version):
        errors.append("VERSION 必须使用语义化版本号，例如 0.1.0")

    if not changelog_path.exists():
        errors.append("CHANGELOG.md 文件缺失")
    elif f"## {version}" not in changelog_path.read_text(encoding="utf-8"):
        errors.append(f"CHANGELOG.md 缺少当前版本 {version} 的记录")

    if not manifest_path.exists():
        errors.append("release/update-manifest.example.json 文件缺失")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"升级清单 JSON 格式错误: {exc}")
        else:
            if manifest.get("version") != version:
                errors.append("升级清单版本号必须与 VERSION 一致")
            platforms = manifest.get("platforms", {})
            for platform in ("darwin-aarch64", "windows-x86_64"):
                if platform not in platforms:
                    errors.append(f"升级清单缺少平台: {platform}")

    if not desktop_package_path.exists():
        errors.append("package.json 桌面打包配置缺失")
    else:
        try:
            package_config = json.loads(desktop_package_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"package.json JSON 格式错误: {exc}")
        else:
            resources = package_config.get("build", {}).get("extraResources", [])
            resource_targets = {
                item.get("to")
                for item in resources
                if isinstance(item, dict)
            }
            if "templates" not in resource_targets:
                errors.append("桌面打包配置缺少 templates 资源")
            if "samples" not in resource_targets:
                errors.append("桌面打包配置缺少 samples 资源")
    if not desktop_main_path.exists():
        errors.append("desktop/main.cjs 桌面壳入口缺失")
    if not desktop_sidecar_script_path.exists():
        errors.append("scripts/build_desktop_sidecar.py 桌面后端打包脚本缺失")
    if not desktop_icon_script_path.exists():
        errors.append("scripts/generate_desktop_icons.py 桌面图标生成脚本缺失")
    if not mac_icon_path.exists():
        errors.append("desktop/resources/icon.icns Mac 图标缺失")
    if not windows_icon_path.exists():
        errors.append("desktop/resources/icon.ico Windows 图标缺失")
    if not sample_order_dir.exists():
        errors.append("脱敏仿真订单样例目录缺失")
    if not sample_pdf_path.exists():
        errors.append("文本型 PDF 示例订单缺失")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate_release_readiness(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Release metadata check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
