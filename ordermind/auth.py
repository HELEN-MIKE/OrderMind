"""本地账号认证模块。

OrderMind 第一版定位是离线桌面应用，因此账号体系不依赖云端服务器。
用户数据保存在本机 JSON 文件中，密码只保存 PBKDF2 加盐哈希。

重要边界：
- 这不是企业统一身份认证系统；
- 第一版适合单机多用户场景；
- 后续如需接入 LDAP、AD 或企业 SSO，可以在本模块外再加适配层。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PBKDF2_ITERATIONS = 210_000
SALT_BYTES = 16


class AuthenticationError(Exception):
    """账号不存在或密码错误。"""


class PasswordChangeRequired(Exception):
    """用户密码正确，但被标记为首次登录必须修改密码。"""


@dataclass(frozen=True)
class AuthSession:
    """认证成功后的轻量会话信息。"""

    username: str
    must_change_password: bool = False


class AuthStore:
    """基于本地 JSON 文件的账号存储。

    该类故意保持很小：只负责创建用户、验证密码、修改密码。
    Web 会话、桌面窗口状态、权限菜单不放在这里，避免认证层和 UI 耦合。
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def create_user(
        self,
        username: str,
        password: str,
        must_change_password: bool = True,
    ) -> None:
        """创建本地用户。

        若用户已存在则抛出 ValueError，避免误覆盖已有密码。
        """

        username = _normalize_username(username)
        _validate_password_strength(password)
        data = self._read()
        if username in data["users"]:
            raise ValueError(f"用户已存在: {username}")
        data["users"][username] = {
            "password_hash": _hash_password(password),
            "must_change_password": must_change_password,
        }
        self._write(data)

    def authenticate(self, username: str, password: str) -> AuthSession:
        """验证账号密码。

        首次登录需要改密时，密码正确也会抛出 PasswordChangeRequired。
        UI 捕获该异常后应跳转到修改密码页。
        """

        user = self._get_user(username)
        if not _verify_password(password, user["password_hash"]):
            raise AuthenticationError("账号或密码错误")
        normalized = _normalize_username(username)
        if user.get("must_change_password", False):
            raise PasswordChangeRequired("首次登录需要修改密码")
        return AuthSession(username=normalized, must_change_password=False)

    def change_password(self, username: str, old_password: str, new_password: str) -> None:
        """修改密码。

        修改前必须验证旧密码；修改后清除首次改密标记。
        """

        user = self._get_user(username)
        if not _verify_password(old_password, user["password_hash"]):
            raise AuthenticationError("原密码错误")
        _validate_password_strength(new_password)
        normalized = _normalize_username(username)
        data = self._read()
        data["users"][normalized]["password_hash"] = _hash_password(new_password)
        data["users"][normalized]["must_change_password"] = False
        self._write(data)

    def ensure_default_admin(self) -> None:
        """确保首次启动时有一个默认管理员账号。

        默认账号仅用于第一版演示和本地试用。因为它被标记为必须改密，
        用户第一次登录后会被引导修改密码，避免长期使用默认密码。
        """

        data = self._read()
        if data["users"]:
            return
        self.create_user("admin", "Admin123456", must_change_password=True)

    def _get_user(self, username: str) -> dict[str, Any]:
        normalized = _normalize_username(username)
        data = self._read()
        user = data["users"].get(normalized)
        if not user:
            raise AuthenticationError("账号或密码错误")
        return user

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"users": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_username(username: str) -> str:
    value = username.strip().lower()
    if not value:
        raise ValueError("用户名不能为空")
    return value


def _validate_password_strength(password: str) -> None:
    """第一版的最低密码要求。

    这里不做过重的企业密码策略，只要求长度够用且包含字母和数字。
    后续可把策略配置化，例如最小长度、特殊字符、过期周期等。
    """

    if len(password) < 8:
        raise ValueError("密码至少需要 8 位")
    if not any(char.isalpha() for char in password):
        raise ValueError("密码需要包含字母")
    if not any(char.isdigit() for char in password):
        raise ValueError("密码需要包含数字")


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return ".".join(
        [
            "pbkdf2_sha256",
            str(PBKDF2_ITERATIONS),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        ]
    )


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split(".", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_text.encode("ascii"))
        expected = base64.b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations_text),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False
