import unittest

from ordermind.i18n import SUPPORTED_LANGUAGES, t
from ordermind.webapp import render_home


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


if __name__ == "__main__":
    unittest.main()
