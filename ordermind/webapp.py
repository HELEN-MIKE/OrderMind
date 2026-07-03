from __future__ import annotations

import errno
import html
import json
import os
import secrets
import sys
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ordermind.auth import (
    AuthStore,
    AuthenticationError,
    PasswordChangeRequired,
)
from ordermind.extractors.dispatcher import parse_order_file
from ordermind.i18n import normalize_language, t
from ordermind.reporting import build_result_payload, payload_to_json
from ordermind.rules import validate_order
from ordermind.templates import load_template

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "templates"
DATA_DIR = Path(os.environ.get("ORDERMIND_DATA_DIR", ROOT / "data"))
AUTH_STORE = AuthStore(DATA_DIR / "users.json")
SESSIONS: dict[str, str] = {}


class OrderMindHandler(BaseHTTPRequestHandler):
    """OrderMind 本地 Web 服务请求处理器。

    第一版使用 Python 标准库实现，是为了减少安装门槛：客户电脑只要有打包后的
    Python 运行环境即可，不需要额外部署后端服务器。后续桌面壳可以把这个服务
    作为本地 worker，也可以直接复用解析/校验核心。
    """

    server_version = "OrderMind/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        lang = _lang_from_query(parsed.query)
        if parsed.path == "/health":
            self._send_health()
            return
        if parsed.path == "/login":
            self._send_html(render_login(lang=lang))
            return
        if parsed.path == "/logout":
            self._logout(lang)
            return
        if parsed.path == "/change-password":
            self._send_html(render_change_password(lang=lang))
            return
        if parsed.path == "/":
            if not self._current_username():
                self._redirect(f"/login?lang={lang}")
                return
            self._send_html(render_home(lang=lang))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/login":
            self._handle_login()
            return
        if parsed.path == "/change-password":
            self._handle_change_password()
            return
        if parsed.path != "/analyze":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not self._current_username():
            self._redirect("/login")
            return
        try:
            form = self._parse_multipart()
            upload = form.get("order_file")
            template_name = form.get("template_name", "default_order_rules.json")
            lang = normalize_language(str(form.get("lang") or "zh"))
            if not upload or not isinstance(upload, UploadedFile):
                self._send_html(
                    render_home(lang=lang, error=t(lang, "choose_file_error")),
                    HTTPStatus.BAD_REQUEST,
                )
                return
            payload = analyze_upload(upload, template_name)
            self._send_html(render_result(payload, lang=lang))
        except Exception as exc:  # noqa: BLE001 - show local user actionable error
            self._send_html(render_home(error=str(exc)), HTTPStatus.BAD_REQUEST)

    def _handle_login(self) -> None:
        form = self._parse_urlencoded()
        lang = normalize_language(form.get("lang", "zh"))
        username = form.get("username", "")
        password = form.get("password", "")
        try:
            session = AUTH_STORE.authenticate(username, password)
        except PasswordChangeRequired:
            self._send_html(render_change_password(lang=lang, username=username))
            return
        except AuthenticationError:
            self._send_html(render_login(lang=lang, error=t(lang, "login_failed")))
            return
        token = secrets.token_urlsafe(32)
        SESSIONS[token] = session.username
        self._redirect(f"/?lang={lang}", cookie=f"ordermind_session={token}; HttpOnly; SameSite=Lax")

    def _handle_change_password(self) -> None:
        form = self._parse_urlencoded()
        lang = normalize_language(form.get("lang", "zh"))
        username = form.get("username", "")
        old_password = form.get("old_password", "")
        new_password = form.get("new_password", "")
        try:
            AUTH_STORE.change_password(username, old_password, new_password)
        except (AuthenticationError, ValueError) as exc:
            self._send_html(
                render_change_password(lang=lang, username=username, error=str(exc)),
                HTTPStatus.BAD_REQUEST,
            )
            return
        self._send_html(render_login(lang=lang, notice=t(lang, "password_changed")))

    def _parse_multipart(self) -> dict[str, object]:
        """解析 multipart/form-data。

        这里没有引入第三方 Web 框架，因此手写了一个只满足本项目上传表单的解析器。
        它不追求通用性，只处理普通文本字段和单个文件字段。
        """

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            return {}
        boundary_marker = "boundary="
        boundary = content_type.split(boundary_marker, 1)[-1].encode()
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        parts = body.split(b"--" + boundary)
        form: dict[str, object] = {}
        for part in parts:
            if b"\r\n\r\n" not in part:
                continue
            header_blob, content = part.split(b"\r\n\r\n", 1)
            content = content.rstrip(b"\r\n-")
            headers = header_blob.decode(errors="ignore")
            disposition = _header_line(headers, "Content-Disposition")
            name = _disposition_value(disposition, "name")
            filename = _disposition_value(disposition, "filename")
            if not name:
                continue
            if filename:
                form[name] = UploadedFile(filename=Path(filename).name, content=content)
            else:
                form[name] = content.decode("utf-8", errors="ignore")
        return form

    def _parse_urlencoded(self) -> dict[str, str]:
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8", errors="ignore")
        parsed = parse_qs(body)
        return {key: values[0] for key, values in parsed.items()}

    def _send_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_health(self) -> None:
        encoded = json.dumps({"status": "ok"}, separators=(",", ":")).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _redirect(self, location: str, cookie: str = "") -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def _current_username(self) -> str:
        cookie_header = self.headers.get("Cookie", "")
        cookies = _parse_cookie_header(cookie_header)
        token = cookies.get("ordermind_session", "")
        return SESSIONS.get(token, "")

    def _logout(self, lang: str) -> None:
        cookie_header = self.headers.get("Cookie", "")
        cookies = _parse_cookie_header(cookie_header)
        token = cookies.get("ordermind_session", "")
        if token:
            SESSIONS.pop(token, None)
        self._redirect(
            f"/login?lang={lang}",
            cookie="ordermind_session=; Max-Age=0; HttpOnly; SameSite=Lax",
        )

    def log_message(self, format: str, *args: object) -> None:
        print(f"[OrderMind] {self.address_string()} - {format % args}")


class UploadedFile:
    """上传文件的轻量包装对象。"""

    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self.content = content


def analyze_upload(upload: UploadedFile, template_name: str) -> dict[str, object]:
    """把上传文件落到临时目录，完成解析、规则校验并返回结构化结果。"""

    template_path = _safe_template_path(template_name)
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / upload.filename
        file_path.write_bytes(upload.content)
        record = parse_order_file(file_path)
    template = load_template(template_path)
    report = validate_order(record, template)
    return build_result_payload(record, report)


def render_login(lang: str = "zh", error: str = "", notice: str = "") -> str:
    """渲染登录页。"""

    lang = normalize_language(lang)
    switch_lang = t(lang, "switch_language_code")
    error_html = f'<div class="alert">{html.escape(error)}</div>' if error else ""
    notice_html = f'<div class="notice">{html.escape(notice)}</div>' if notice else ""
    return f"""<!doctype html>
<html lang="{_html_lang(lang)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(t(lang, "login_title"))}</title>
  <style>{STYLE}</style>
</head>
<body>
  <main class="auth-shell">
    <section class="panel auth-panel">
      <div class="auth-head">
        <div>
          <p class="eyebrow">{html.escape(t(lang, "app_title"))}</p>
          <h1>{html.escape(t(lang, "login_title"))}</h1>
        </div>
        <a class="link-button" href="/login?lang={html.escape(switch_lang)}">{html.escape(t(lang, "switch_language"))}</a>
      </div>
      {error_html}
      {notice_html}
      <form method="post" action="/login" class="stack-form">
        <input type="hidden" name="lang" value="{html.escape(lang)}">
        <label><span>{html.escape(t(lang, "username"))}</span><input name="username" autocomplete="username" required></label>
        <label><span>{html.escape(t(lang, "password"))}</span><input name="password" type="password" autocomplete="current-password" required></label>
        <button type="submit">{html.escape(t(lang, "login"))}</button>
      </form>
      <p class="hint">{html.escape(t(lang, "demo_account_hint"))}</p>
    </section>
  </main>
</body>
</html>"""


def render_change_password(
    lang: str = "zh",
    username: str = "",
    error: str = "",
) -> str:
    """渲染首次登录修改密码页。"""

    lang = normalize_language(lang)
    error_html = f'<div class="alert">{html.escape(error)}</div>' if error else ""
    return f"""<!doctype html>
<html lang="{_html_lang(lang)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(t(lang, "change_password_title"))}</title>
  <style>{STYLE}</style>
</head>
<body>
  <main class="auth-shell">
    <section class="panel auth-panel">
      <p class="eyebrow">{html.escape(t(lang, "app_title"))}</p>
      <h1>{html.escape(t(lang, "change_password_title"))}</h1>
      <p class="hint">{html.escape(t(lang, "change_password_hint"))}</p>
      {error_html}
      <form method="post" action="/change-password" class="stack-form">
        <input type="hidden" name="lang" value="{html.escape(lang)}">
        <label><span>{html.escape(t(lang, "username"))}</span><input name="username" value="{html.escape(username)}" autocomplete="username" required></label>
        <label><span>{html.escape(t(lang, "old_password"))}</span><input name="old_password" type="password" autocomplete="current-password" required></label>
        <label><span>{html.escape(t(lang, "new_password"))}</span><input name="new_password" type="password" autocomplete="new-password" required></label>
        <button type="submit">{html.escape(t(lang, "change_password"))}</button>
      </form>
    </section>
  </main>
</body>
</html>"""


def render_home(lang: str = "zh", error: str = "") -> str:
    """渲染首页。

    `lang` 来自 URL 查询参数或表单隐藏字段。文案统一从 i18n 模块读取，
    避免以后桌面版、Web 版和报告导出各写一套翻译。
    """

    lang = normalize_language(lang)
    switch_lang = t(lang, "switch_language_code")
    options = "\n".join(
        f'<option value="{html.escape(path.name)}">{html.escape(path.stem)}</option>'
        for path in sorted(TEMPLATE_DIR.glob("*.json"))
    )
    error_html = f'<div class="alert">{html.escape(error)}</div>' if error else ""
    guide_items = "\n".join(
        f"""<li>
          <strong>{html.escape(t(lang, f"guide_step_{index}_title"))}</strong>
          <span>{html.escape(t(lang, f"guide_step_{index}_body"))}</span>
        </li>"""
        for index in range(1, 5)
    )
    return f"""<!doctype html>
<html lang="{_html_lang(lang)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(t(lang, "app_title"))}</title>
  <style>{STYLE}</style>
</head>
<body>
  <main class="shell">
    <section class="topbar">
      <div>
        <p class="eyebrow">{html.escape(t(lang, "app_title"))}</p>
        <h1>{html.escape(t(lang, "workspace_title"))}</h1>
      </div>
      <div class="top-actions">
        <a class="link-button" href="/?lang={html.escape(switch_lang)}">{html.escape(t(lang, "switch_language"))}</a>
        <a class="link-button" href="/logout?lang={html.escape(lang)}">{html.escape(t(lang, "logout"))}</a>
        <span class="status">{html.escape(t(lang, "privacy_badge"))}</span>
      </div>
    </section>
    {error_html}
    <section class="panel">
      <form action="/analyze" method="post" enctype="multipart/form-data" class="upload-form">
        <input type="hidden" name="lang" value="{html.escape(lang)}">
        <label>
          <span>{html.escape(t(lang, "order_file"))}</span>
          <input type="file" name="order_file" accept=".txt,.csv,.tsv,.xlsx,.xlsm" required>
        </label>
        <label>
          <span>{html.escape(t(lang, "rule_template"))}</span>
          <select name="template_name">{options}</select>
        </label>
        <button type="submit">{html.escape(t(lang, "start_review"))}</button>
      </form>
    </section>
    <section class="panel guide-panel">
      <h2>{html.escape(t(lang, "first_time_guide"))}</h2>
      <ol class="guide-list">{guide_items}</ol>
    </section>
    <section class="grid">
      <div class="metric"><strong>{html.escape(t(lang, "current_version"))}</strong><span>{html.escape(t(lang, "supported_formats"))}</span></div>
      <div class="metric"><strong>{html.escape(t(lang, "validation_scope"))}</strong><span>{html.escape(t(lang, "validation_scope_value"))}</span></div>
      <div class="metric"><strong>{html.escape(t(lang, "roadmap"))}</strong><span>{html.escape(t(lang, "roadmap_value"))}</span></div>
    </section>
  </main>
</body>
</html>"""


def render_result(payload: dict[str, object], lang: str = "zh") -> str:
    """渲染审单结果页。"""

    lang = normalize_language(lang)
    record = payload["record"]
    report = payload["report"]
    summary = payload["summary"]
    lines = record["lines"]
    issues = report["errors"] + report["warnings"] + report["infos"]
    line_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(line.get('item_no') or '')}</td>"
        f"<td>{html.escape(line.get('product_name') or '')}</td>"
        f"<td>{html.escape(line.get('quantity') or '')}</td>"
        f"<td>{html.escape(line.get('unit_price') or '')}</td>"
        f"<td>{html.escape(line.get('subtotal') or '')}</td>"
        f"<td>{html.escape(line.get('material') or '')}</td>"
        "</tr>"
        for line in lines
    )
    issue_rows = "\n".join(
        "<tr>"
        f"<td><span class='pill {html.escape(issue['severity'])}'>{html.escape(issue['severity'])}</span></td>"
        f"<td>{html.escape(issue['location'])}</td>"
        f"<td>{html.escape(issue['message'])}</td>"
        "</tr>"
        for issue in issues
    ) or "<tr><td colspan='3'>未发现错误或警告。</td></tr>"
    json_payload = html.escape(payload_to_json(payload))
    return f"""<!doctype html>
<html lang="{_html_lang(lang)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(t(lang, "result_title"))} - OrderMind</title>
  <style>{STYLE}</style>
</head>
<body>
  <main class="shell">
    <section class="topbar">
      <div>
        <p class="eyebrow">{html.escape(t(lang, "result_title"))}</p>
        <h1>{html.escape(record['source_name'])}</h1>
      </div>
      <a class="link-button" href="/?lang={html.escape(lang)}">{html.escape(t(lang, "upload_again"))}</a>
    </section>
    <section class="grid">
      <div class="metric"><strong>{summary['line_count']}</strong><span>{html.escape(t(lang, "line_count"))}</span></div>
      <div class="metric danger"><strong>{summary['error_count']}</strong><span>{html.escape(t(lang, "errors"))}</span></div>
      <div class="metric warn"><strong>{summary['warning_count']}</strong><span>{html.escape(t(lang, "warnings"))}</span></div>
    </section>
    <section class="panel">
      <h2>{html.escape(t(lang, "order_lines"))}</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>{html.escape(t(lang, "item_no"))}</th><th>{html.escape(t(lang, "product_name"))}</th><th>{html.escape(t(lang, "quantity"))}</th><th>{html.escape(t(lang, "unit_price"))}</th><th>{html.escape(t(lang, "subtotal"))}</th><th>{html.escape(t(lang, "material"))}</th></tr></thead>
          <tbody>{line_rows}</tbody>
        </table>
      </div>
    </section>
    <section class="panel">
      <h2>{html.escape(t(lang, "issues"))}</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>{html.escape(t(lang, "severity"))}</th><th>{html.escape(t(lang, "location"))}</th><th>{html.escape(t(lang, "issue"))}</th></tr></thead>
          <tbody>{issue_rows}</tbody>
        </table>
      </div>
    </section>
    <section class="panel">
      <h2>{html.escape(t(lang, "structured_json"))}</h2>
      <pre>{json_payload}</pre>
    </section>
  </main>
</body>
</html>"""


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    """启动本地 Web 服务。"""

    host = os.environ.get("ORDERMIND_HOST", host)
    port = _port_from_env(port)
    configure_runtime_from_environment()
    AUTH_STORE.ensure_default_admin()
    try:
        server = ThreadingHTTPServer((host, port), OrderMindHandler)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            print(
                "\n".join(
                    [
                        f"OrderMind 启动失败：端口 {port} 已被占用。",
                        f"如果应用已经打开，请直接访问 http://{host}:{port}",
                        "如果要再启动一个实例，请换一个端口，例如：",
                        f"ORDERMIND_PORT={port + 1} python3 run_app.py",
                    ]
                ),
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        raise
    print(f"OrderMind 订单智脑已启动: http://{host}:{port}")
    server.serve_forever()


def configure_runtime_from_environment() -> AuthStore:
    """根据桌面壳传入的环境变量配置本地运行目录。"""

    global AUTH_STORE, DATA_DIR

    DATA_DIR = Path(os.environ.get("ORDERMIND_DATA_DIR", ROOT / "data"))
    AUTH_STORE = AuthStore(DATA_DIR / "users.json")
    return AUTH_STORE


def _port_from_env(default: int) -> int:
    value = os.environ.get("ORDERMIND_PORT")
    if value is None:
        return default
    try:
        port = int(value)
    except ValueError as exc:
        raise SystemExit(f"ORDERMIND_PORT 必须是数字，当前值：{value}") from exc
    if not 1 <= port <= 65535:
        raise SystemExit(f"ORDERMIND_PORT 必须在 1 到 65535 之间，当前值：{value}")
    return port


def _safe_template_path(template_name: str) -> Path:
    """只允许从内置模板目录读取文件，避免路径穿越。"""

    path = TEMPLATE_DIR / Path(template_name).name
    if not path.exists():
        raise ValueError(f"规则模板不存在: {template_name}")
    return path


def _header_line(headers: str, name: str) -> str:
    for line in headers.splitlines():
        if line.lower().startswith(name.lower() + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def _disposition_value(disposition: str, key: str) -> str:
    for part in disposition.split(";"):
        part = part.strip()
        if part.startswith(key + "="):
            return part.split("=", 1)[1].strip().strip('"')
    return ""


def _lang_from_query(query: str) -> str:
    params = parse_qs(query)
    return normalize_language((params.get("lang") or ["zh"])[0])


def _parse_cookie_header(cookie_header: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for part in cookie_header.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        cookies[key.strip()] = value.strip()
    return cookies


def _html_lang(lang: str) -> str:
    return "zh-CN" if normalize_language(lang) == "zh" else "en"


STYLE = """
:root {
  color-scheme: light;
  --bg: #eef2f4;
  --ink: #162026;
  --muted: #66737c;
  --line: #ccd6dc;
  --panel: #ffffff;
  --accent: #0f766e;
  --danger: #b42318;
  --warn: #b7791f;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--ink);
}
.auth-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
}
.auth-panel {
  width: min(480px, 100%);
  margin: 0;
}
.auth-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}
.stack-form {
  display: grid;
  gap: 14px;
}
.hint {
  margin: 14px 0 0;
  color: var(--muted);
  line-height: 1.6;
}
.shell { width: min(1120px, calc(100vw - 32px)); margin: 32px auto; }
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.top-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.eyebrow { margin: 0 0 6px; color: var(--accent); font-size: 13px; font-weight: 700; }
h1 { margin: 0; font-size: clamp(26px, 4vw, 42px); letter-spacing: 0; }
h2 { margin: 0 0 16px; font-size: 20px; }
.status, .link-button {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px 12px;
  background: #f8fafb;
  color: var(--muted);
  text-decoration: none;
  white-space: nowrap;
}
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 20px;
  margin: 16px 0;
}
.guide-panel {
  background: #fbfcfd;
}
.guide-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.guide-list li {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: white;
  padding: 14px;
}
.guide-list strong {
  display: block;
  margin-bottom: 8px;
  color: var(--ink);
}
.guide-list span {
  display: block;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.55;
}
.upload-form {
  display: grid;
  grid-template-columns: 1fr 240px auto;
  gap: 16px;
  align-items: end;
}
label span {
  display: block;
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 14px;
}
input, select, button {
  width: 100%;
  min-height: 44px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 9px 12px;
  font: inherit;
}
button {
  border-color: var(--accent);
  background: var(--accent);
  color: white;
  font-weight: 700;
  cursor: pointer;
}
.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.metric {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 16px;
}
.metric strong {
  display: block;
  margin-bottom: 8px;
  font-size: 26px;
}
.metric span { color: var(--muted); }
.metric.danger strong { color: var(--danger); }
.metric.warn strong { color: var(--warn); }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; min-width: 720px; }
th, td {
  border-bottom: 1px solid var(--line);
  padding: 11px 10px;
  text-align: left;
  vertical-align: top;
}
th { color: var(--muted); font-size: 13px; }
.pill {
  display: inline-block;
  border-radius: 999px;
  padding: 3px 8px;
  background: #e8eef1;
}
.pill.error { background: #fde8e6; color: var(--danger); }
.pill.warning { background: #fff4da; color: var(--warn); }
pre {
  max-height: 360px;
  overflow: auto;
  margin: 0;
  padding: 14px;
  border-radius: 8px;
  background: #101820;
  color: #eef6f7;
  font-size: 13px;
}
.alert {
  border: 1px solid #f4b4ae;
  border-radius: 8px;
  padding: 12px 14px;
  background: #fff4f2;
  color: var(--danger);
  margin-bottom: 16px;
}
.notice {
  border: 1px solid #a7d8ce;
  border-radius: 8px;
  padding: 12px 14px;
  background: #eefbf7;
  color: #0f766e;
  margin-bottom: 16px;
}
@media (max-width: 820px) {
  .topbar, .upload-form, .top-actions { display: block; }
  .status, .link-button, input, select, button { margin-top: 12px; }
  .grid, .guide-list { grid-template-columns: 1fr; }
}
"""
