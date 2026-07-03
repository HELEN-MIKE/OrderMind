import errno
import io
import os
import unittest
from contextlib import redirect_stderr
from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ordermind import webapp


class WebappRunTest(unittest.TestCase):
    def test_run_exits_cleanly_when_port_is_in_use(self):
        class DummyAuthStore:
            def ensure_default_admin(self):
                return None

        stderr = io.StringIO()
        with (
            patch.object(webapp, "AUTH_STORE", DummyAuthStore()),
            patch.object(
                webapp,
                "ThreadingHTTPServer",
                side_effect=OSError(errno.EADDRINUSE, "Address already in use"),
            ),
            self.assertRaises(SystemExit) as raised,
            redirect_stderr(stderr),
        ):
            webapp.run(host="127.0.0.1", port=8765)

        self.assertEqual(raised.exception.code, 1)
        self.assertIn("端口 8765 已被占用", stderr.getvalue())
        self.assertIn("http://127.0.0.1:8765", stderr.getvalue())
        self.assertIn("ORDERMIND_PORT=8766 python3 run_app.py", stderr.getvalue())

    def test_health_endpoint_returns_ok_without_authentication(self):
        class DummyHandler(webapp.OrderMindHandler):
            def __init__(self):
                self.status = None
                self.headers = []
                self.wfile = io.BytesIO()

            def send_response(self, status):
                self.status = status

            def send_header(self, name, value):
                self.headers.append((name, value))

            def end_headers(self):
                return None

        handler = DummyHandler()
        handler._send_health()

        self.assertEqual(handler.status, HTTPStatus.OK)
        self.assertIn(("Content-Type", "application/json; charset=utf-8"), handler.headers)
        self.assertEqual(handler.wfile.getvalue(), b'{"status":"ok"}')

    def test_configure_runtime_uses_desktop_data_directory_from_environment(self):
        with TemporaryDirectory() as tmpdir, patch.dict(
            os.environ,
            {"ORDERMIND_DATA_DIR": tmpdir},
            clear=False,
        ):
            auth_store = webapp.configure_runtime_from_environment()

        self.assertEqual(webapp.DATA_DIR, Path(tmpdir))
        self.assertEqual(auth_store.path, Path(tmpdir) / "users.json")


if __name__ == "__main__":
    unittest.main()
