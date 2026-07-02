import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from ordermind.templates import load_template


class TemplateLoaderTest(unittest.TestCase):
    def test_load_template_converts_decimal_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "template.json"
            path.write_text(
                json.dumps(
                    {
                        "name": "默认审单规则",
                        "required_fields": ["item_no", "product_name"],
                        "item_no_pattern": "^OM-\\d{4}$",
                        "total_amount_tolerance": "0.05",
                        "line_amount_tolerance": "0.02",
                        "decimal_places": 2,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            template = load_template(path)

        self.assertEqual(template.name, "默认审单规则")
        self.assertEqual(template.total_amount_tolerance, Decimal("0.05"))
        self.assertEqual(template.line_amount_tolerance, Decimal("0.02"))
        self.assertEqual(template.required_fields, ["item_no", "product_name"])


if __name__ == "__main__":
    unittest.main()
