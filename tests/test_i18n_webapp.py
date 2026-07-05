import unittest

from ordermind.i18n import SUPPORTED_LANGUAGES, t
from ordermind.webapp import render_export_report, render_home, render_result, sample_order_options


class I18nWebappTest(unittest.TestCase):
    def test_supported_languages_include_chinese_and_english(self):
        self.assertIn("zh", SUPPORTED_LANGUAGES)
        self.assertIn("en", SUPPORTED_LANGUAGES)
        self.assertEqual(t("zh", "app_title"), "OrderMind 订单智脑")
        self.assertEqual(t("en", "workspace_title"), "Offline Order Review Workspace")

    def test_home_page_renders_selected_language(self):
        chinese = render_home(lang="zh")
        english = render_home(lang="en")

        self.assertIn("离线智能审单工作台", chinese)
        self.assertIn("首次使用指引", chinese)
        self.assertIn("第 1 步：选择订单文件", chinese)
        self.assertIn("Offline Order Review Workspace", english)
        self.assertIn("First-Time Guide", english)
        self.assertIn("Step 1: Choose an order file", english)
        self.assertIn("?lang=en", chinese)
        self.assertIn("?lang=zh", english)
        self.assertIn('action="/analyze-sample"', chinese)
        self.assertIn("脱敏示例订单", chinese)
        self.assertIn("Sanitized Sample Orders", english)
        self.assertIn(".png", chinese)
        self.assertIn(".jpg", chinese)
        self.assertIn("图片 OCR", chinese)
        self.assertIn("image OCR", english)

    def test_sample_order_options_only_expose_curated_examples(self):
        options = sample_order_options()
        names = [option["filename"] for option in options]

        self.assertIn("domestic_purchase_order_zh.txt", names)
        self.assertIn("review_findings_bad_amount_missing_material.txt", names)
        self.assertNotIn("README.md", names)

    def test_result_page_renders_empty_issue_message_in_selected_language(self):
        payload = {
            "record": {"source_name": "sample_order.txt", "lines": []},
            "report": {"errors": [], "warnings": [], "infos": []},
            "summary": {
                "line_count": 0,
                "error_count": 0,
                "warning_count": 0,
                "info_count": 0,
            },
        }

        chinese = render_result(payload, lang="zh")
        english = render_result(payload, lang="en")

        self.assertIn("未发现错误或警告。", chinese)
        self.assertIn("No errors or warnings found.", english)
        self.assertNotIn("未发现错误或警告。", english)

    def test_result_page_offers_local_report_export(self):
        payload = {
            "record": {"source_name": "sample_order.txt", "lines": []},
            "report": {"errors": [], "warnings": [], "infos": []},
            "summary": {
                "line_count": 0,
                "error_count": 0,
                "warning_count": 0,
                "info_count": 0,
            },
        }

        page = render_result(payload, lang="en")

        self.assertIn('action="/export-report"', page)
        self.assertIn('name="format" value="html"', page)
        self.assertIn('name="format" value="xlsx"', page)
        self.assertIn('name="payload_json"', page)
        self.assertIn("Export Report", page)
        self.assertIn("Export Excel", page)

    def test_export_report_renders_a_standalone_html_report(self):
        payload = {
            "record": {
                "source_name": "sample_order.txt",
                "lines": [
                    {
                        "item_no": "OM-1001",
                        "product_name": "不锈钢杯",
                        "quantity": "120",
                        "unit_price": "2.50",
                        "subtotal": "300.00",
                        "material": "304不锈钢",
                    }
                ],
            },
            "report": {
                "errors": [],
                "warnings": [
                    {
                        "severity": "warning",
                        "code": "CHECK_SAMPLE",
                        "location": "row 1",
                        "message": "需要人工复核",
                    }
                ],
                "infos": [],
            },
            "summary": {
                "line_count": 1,
                "error_count": 0,
                "warning_count": 1,
                "info_count": 0,
            },
        }

        report = render_export_report(payload, lang="zh")

        self.assertIn("<!doctype html>", report)
        self.assertIn("OrderMind 审单报告", report)
        self.assertIn("sample_order.txt", report)
        self.assertIn("OM-1001", report)
        self.assertIn("需要人工复核", report)
        self.assertIn("结构化 JSON", report)


if __name__ == "__main__":
    unittest.main()
