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
    desktop_python_launcher_path = root / "scripts" / "run_python.cjs"
    desktop_builder_launcher_path = root / "scripts" / "run_electron_builder.cjs"
    signing_check_script_path = root / "scripts" / "check_signing_environment.py"
    update_manifest_script_path = root / "scripts" / "generate_update_manifest.py"
    mac_notarize_hook_path = root / "scripts" / "notarize_mac.cjs"
    windows_sign_hook_path = root / "scripts" / "sign_windows.cjs"
    desktop_icon_script_path = root / "scripts" / "generate_desktop_icons.py"
    mac_icon_path = root / "desktop" / "resources" / "icon.icns"
    windows_icon_path = root / "desktop" / "resources" / "icon.ico"
    release_workflow_path = root / ".github" / "workflows" / "release-build.yml"
    ocr_extractor_path = root / "ordermind" / "extractors" / "ocr.py"
    sample_order_dir = root / "samples" / "customer_like_orders"
    sample_pdf_path = sample_order_dir / "text_pdf_order.pdf"
    signing_docs_path = root / "docs" / "signing-and-updates.md"

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
            dependencies = package_config.get("dependencies", {})
            if "electron-updater" not in dependencies:
                errors.append("桌面包缺少 electron-updater 自动更新依赖")
            build_config = package_config.get("build", {})
            publish = build_config.get("publish", {})
            if publish.get("provider") != "generic":
                errors.append("桌面打包配置缺少 generic publish 自动更新配置")
            if build_config.get("afterSign") != "scripts/notarize_mac.cjs":
                errors.append("桌面打包配置缺少 macOS 公证 afterSign hook")
            if build_config.get("win", {}).get("signtoolOptions", {}).get("sign") != "scripts/sign_windows.cjs":
                errors.append("桌面打包配置缺少 Windows 签名 hook")
            scripts = package_config.get("scripts", {})
            sidecar_command = scripts.get("desktop:sidecar")
            if sidecar_command != "node scripts/run_python.cjs scripts/build_desktop_sidecar.py":
                errors.append("desktop:sidecar 必须使用跨平台 Python 启动器")
            for script_name, command in scripts.items():
                if isinstance(command, str) and "ELECTRON_MIRROR=" in command:
                    errors.append(f"{script_name} 不能使用行内 ELECTRON_MIRROR 写法")
            for script_name in ("desktop:package", "desktop:dist:mac", "desktop:dist:win"):
                command = scripts.get(script_name, "")
                if "node scripts/run_electron_builder.cjs" not in command:
                    errors.append(f"{script_name} 必须使用跨平台 electron-builder 启动器")
            if "release:check-signing" not in scripts:
                errors.append("package.json 缺少 release:check-signing 脚本")
            if "release:manifest" not in scripts:
                errors.append("package.json 缺少 release:manifest 脚本")
    if not desktop_main_path.exists():
        errors.append("desktop/main.cjs 桌面壳入口缺失")
    else:
        desktop_main_text = desktop_main_path.read_text(encoding="utf-8")
        for snippet in ("checkForUpdates", "downloadUpdate", "update-downloaded", "quitAndInstall"):
            if snippet not in desktop_main_text:
                errors.append(f"desktop/main.cjs 自动更新流程缺少 {snippet}")
    if not desktop_sidecar_script_path.exists():
        errors.append("scripts/build_desktop_sidecar.py 桌面后端打包脚本缺失")
    if not desktop_python_launcher_path.exists():
        errors.append("scripts/run_python.cjs 跨平台 Python 启动器缺失")
    if not desktop_builder_launcher_path.exists():
        errors.append("scripts/run_electron_builder.cjs 跨平台 electron-builder 启动器缺失")
    elif "ORDERMIND_UPDATE_BASE_URL" not in desktop_builder_launcher_path.read_text(encoding="utf-8"):
        errors.append("scripts/run_electron_builder.cjs 缺少自动更新地址默认值")
    if not signing_check_script_path.exists():
        errors.append("scripts/check_signing_environment.py 签名环境检查脚本缺失")
    if not update_manifest_script_path.exists():
        errors.append("scripts/generate_update_manifest.py 更新清单生成脚本缺失")
    if not mac_notarize_hook_path.exists():
        errors.append("scripts/notarize_mac.cjs macOS 公证 hook 缺失")
    if not windows_sign_hook_path.exists():
        errors.append("scripts/sign_windows.cjs Windows 签名 hook 缺失")
    if not desktop_icon_script_path.exists():
        errors.append("scripts/generate_desktop_icons.py 桌面图标生成脚本缺失")
    if not mac_icon_path.exists():
        errors.append("desktop/resources/icon.icns Mac 图标缺失")
    if not windows_icon_path.exists():
        errors.append("desktop/resources/icon.ico Windows 图标缺失")
    if not release_workflow_path.exists():
        errors.append(".github/workflows/release-build.yml Windows/macOS 安装包 CI 缺失")
    if not ocr_extractor_path.exists():
        errors.append("ordermind/extractors/ocr.py OCR 解析器缺失")
    webapp_path = root / "ordermind" / "webapp.py"
    if not webapp_path.exists():
        errors.append("ordermind/webapp.py 本地 Web 工作台缺失")
    else:
        webapp_text = webapp_path.read_text(encoding="utf-8")
        if "/templates" not in webapp_text or "/templates/save" not in webapp_text:
            errors.append("本地 Web 工作台缺少规则模板管理页面或保存路由")
    if not sample_order_dir.exists():
        errors.append("脱敏仿真订单样例目录缺失")
    if not sample_pdf_path.exists():
        errors.append("文本型 PDF 示例订单缺失")
    if not signing_docs_path.exists():
        errors.append("docs/signing-and-updates.md 签名和自动更新文档缺失")

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
