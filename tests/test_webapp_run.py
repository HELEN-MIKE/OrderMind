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

    def test_configure_runtime_uses_desktop_resource_directory_from_environment(self):
        with TemporaryDirectory() as tmpdir, patch.dict(
            os.environ,
            {"ORDERMIND_RESOURCE_DIR": tmpdir},
            clear=False,
        ):
            webapp.configure_runtime_from_environment()

        self.assertEqual(webapp.RESOURCE_DIR, Path(tmpdir))
        self.assertEqual(webapp.TEMPLATE_DIR, Path(tmpdir) / "templates")
        self.assertEqual(webapp.SAMPLE_ORDER_DIR, Path(tmpdir) / "samples" / "customer_like_orders")

        with patch.dict(os.environ, {}, clear=True):
            webapp.configure_runtime_from_environment()

    def test_download_filename_is_safe_and_html_extension(self):
        self.assertEqual(
            webapp._download_filename("客户订单 2026/07/03.xlsx"),
            "客户订单_2026_07_03-report.html",
        )
        self.assertEqual(
            webapp._download_filename("../bad:name?.txt"),
            "bad_name-report.html",
        )

    def test_safe_sample_path_rejects_unknown_or_nested_names(self):
        with self.assertRaises(ValueError):
            webapp._safe_sample_path("../sample_order.txt")
        with self.assertRaises(ValueError):
            webapp._safe_sample_path("README.md")

        sample_path = webapp._safe_sample_path("domestic_purchase_order_zh.txt")
        self.assertEqual(sample_path.name, "domestic_purchase_order_zh.txt")


if __name__ == "__main__":
    unittest.main()
