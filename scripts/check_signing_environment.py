"""检查正式签名、公证、自动更新所需环境。

脚本只报告缺失项，不打印任何证书密码、Apple 密钥或令牌内容。CI 可以先运行
它来区分“未配置证书”和“构建脚本坏了”。
"""

from __future__ import annotations

import os
import platform
import shutil


MAC_ENV_VARS = (
    "APPLE_ID",
    "APPLE_APP_SPECIFIC_PASSWORD",
    "APPLE_TEAM_ID",
)
WINDOWS_ENV_VARS = (
    "WINDOWS_CERTIFICATE_FILE",
    "WINDOWS_CERTIFICATE_PASSWORD",
)
UPDATE_ENV_VARS = ("ORDERMIND_UPDATE_BASE_URL",)


def signing_environment_status() -> dict[str, object]:
    """返回当前机器签名、公证和更新发布配置状态。"""

    system = platform.system().lower()
    missing: list[str] = []
    warnings: list[str] = []

    for name in UPDATE_ENV_VARS:
        if not os.environ.get(name):
            warnings.append(f"{name} 未配置，自动更新发布地址将不可用")

    if system == "darwin":
        missing.extend(name for name in MAC_ENV_VARS if not os.environ.get(name))
        if not shutil.which("xcrun"):
            missing.append("xcrun/notarytool")
    elif system == "windows":
        missing.extend(name for name in WINDOWS_ENV_VARS if not os.environ.get(name))
        if not shutil.which("signtool"):
            warnings.append("signtool 未在 PATH 中，electron-builder 可能需要自行定位 Windows SDK")
    else:
        warnings.append("当前平台不执行 macOS 公证或 Windows 签名")

    return {
        "platform": system,
        "ready": not missing,
        "missing": missing,
        "warnings": warnings,
    }


def main() -> int:
    status = signing_environment_status()
    for warning in status["warnings"]:
        print(f"WARN: {warning}")
    if status["missing"]:
        for item in status["missing"]:
            print(f"MISSING: {item}")
        return 1
    print("Signing environment check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
