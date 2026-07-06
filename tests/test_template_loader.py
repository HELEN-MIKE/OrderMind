import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from ordermind.templates import load_template
from ordermind import webapp


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

    def test_template_manager_saves_user_template_in_data_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            with patch.object(webapp, "DATA_DIR", data_dir):
                saved_path = webapp.save_user_template_from_form(
                    {
                        "name": "客户A规则",
                        "required_fields": "item_no, product_name, quantity",
                        "item_no_pattern": "^A-\\d{3}$",
                        "allowed_units": "PCS, SET",
                        "total_amount_tolerance": "0.10",
                        "line_amount_tolerance": "0.03",
                        "decimal_places": "2",
                        "quantity_tolerance": "0",
                        "material_keywords": "304, silicone",
                        "packaging_keywords": "carton",
                    }
                )

            template = load_template(saved_path)

        self.assertEqual(saved_path.name, "客户A规则.json")
        self.assertEqual(saved_path.parent.name, "templates")
        self.assertEqual(template.name, "客户A规则")
        self.assertEqual(template.required_fields, ["item_no", "product_name", "quantity"])
        self.assertEqual(template.allowed_units, ["PCS", "SET"])
        self.assertEqual(template.total_amount_tolerance, Decimal("0.10"))
        self.assertEqual(template.material_keywords, ["304", "silicone"])

    def test_template_manager_rejects_unsafe_template_name(self):
        with self.assertRaises(ValueError):
            webapp.save_user_template_from_form({"name": "../bad", "decimal_places": "2"})


if __name__ == "__main__":
    unittest.main()
