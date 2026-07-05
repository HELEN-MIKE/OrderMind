import unittest
from decimal import Decimal
from pathlib import Path

from ordermind.extractors.dispatcher import parse_order_file
from ordermind.rules import validate_order
from ordermind.templates import load_template


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "samples" / "customer_like_orders"
TEMPLATE_PATH = ROOT / "templates" / "default_order_rules.json"


class CustomerLikeSamplesTest(unittest.TestCase):
    def setUp(self):
        self.template = load_template(TEMPLATE_PATH)

    def test_sanitized_customer_like_samples_are_parseable(self):
        cases = {
            "domestic_purchase_order_zh.txt": {
                "line_count": 3,
                "total_amount": Decimal("29280.00"),
                "required_terms": ["T/T", "外箱"],
            },
            "commercial_invoice_en.csv": {
                "line_count": 3,
                "total_amount": Decimal("7800.00"),
                "required_terms": ["30% deposit", "export carton"],
            },
            "proforma_invoice_en.tsv": {
                "line_count": 2,
                "total_amount": Decimal("4663.20"),
                "required_terms": ["30 days", "carton"],
            },
            "multi_currency_order.xlsx": {
                "line_count": 3,
                "total_amount": Decimal("10055.00"),
                "required_terms": ["L/C", "carton"],
            },
            "text_pdf_order.pdf": {
                "line_count": 2,
                "total_amount": Decimal("4004.00"),
                "required_terms": ["30% deposit", "carton"],
            },
        }

        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                path = SAMPLE_DIR / filename
                record = parse_order_file(path)
                report = validate_order(record, self.template)

                self.assertEqual(len(record.lines), expected["line_count"])
                self.assertEqual(record.total_amount, expected["total_amount"])
                self.assertFalse(report.errors)
                joined_header = f"{record.payment_terms} {record.packaging_requirements}"
                for term in expected["required_terms"]:
                    self.assertIn(term, joined_header)

    def test_problem_sample_surfaces_expected_review_issues(self):
        record = parse_order_file(SAMPLE_DIR / "review_findings_bad_amount_missing_material.txt")
        report = validate_order(record, self.template)

        issue_codes = [issue.code for issue in report.errors + report.warnings]

        self.assertEqual(len(record.lines), 3)
        self.assertIn("line_amount_mismatch", issue_codes)
        self.assertIn("total_amount_mismatch", issue_codes)
        self.assertIn("required_missing", issue_codes)
        self.assertIn("item_no_format", issue_codes)
        self.assertIn("decimal_places", issue_codes)


if __name__ == "__main__":
    unittest.main()
