import unittest
from decimal import Decimal

from ordermind.extractors.text import parse_text_order
from ordermind.models import OrderLine, OrderRecord
from ordermind.rules import RuleTemplate, validate_order


class CoreEngineTest(unittest.TestCase):
    def test_parse_text_order_extracts_header_and_lines(self):
        text = """
        客户订单
        付款方式: T/T 30% deposit, balance before shipment
        包装要求: 每件独立包装，外箱加贴唛头
        交货期: 2026-08-15

        货号,品名,数量,单价,小计,材质
        OM-1001,不锈钢杯,120,2.50,300.00,304不锈钢
        OM-1002,硅胶盖,120,0.80,96.00,食品级硅胶
        总金额: 396.00
        """

        record = parse_text_order(text, source_name="sample.txt")

        self.assertEqual(record.total_amount, Decimal("396.00"))
        self.assertEqual(record.payment_terms, "T/T 30% deposit, balance before shipment")
        self.assertEqual(record.packaging_requirements, "每件独立包装，外箱加贴唛头")
        self.assertEqual(record.delivery_date, "2026-08-15")
        self.assertEqual(len(record.lines), 2)
        self.assertEqual(record.lines[0].item_no, "OM-1001")
        self.assertEqual(record.lines[0].subtotal, Decimal("300.00"))

    def test_validate_order_accepts_matching_amounts_and_required_fields(self):
        template = RuleTemplate(
            name="客户A",
            required_fields=["item_no", "product_name", "quantity", "unit_price"],
            item_no_pattern=r"^OM-\d{4}$",
            total_amount_tolerance=Decimal("0.01"),
        )
        record = OrderRecord(
            source_name="manual",
            payment_terms="T/T",
            packaging_requirements="Carton",
            lines=[
                OrderLine(
                    item_no="OM-1001",
                    product_name="不锈钢杯",
                    quantity=Decimal("120"),
                    unit_price=Decimal("2.50"),
                    subtotal=Decimal("300.00"),
                ),
                OrderLine(
                    item_no="OM-1002",
                    product_name="硅胶盖",
                    quantity=Decimal("120"),
                    unit_price=Decimal("0.80"),
                    subtotal=Decimal("96.00"),
                ),
            ],
            total_amount=Decimal("396.00"),
        )

        results = validate_order(record, template)

        self.assertEqual(results.errors, [])
        self.assertEqual(results.warnings, [])

    def test_validate_order_reports_amount_quantity_and_format_issues(self):
        template = RuleTemplate(
            name="客户B",
            required_fields=["item_no", "product_name", "quantity", "unit_price"],
            item_no_pattern=r"^OM-\d{4}$",
            total_amount_tolerance=Decimal("0.01"),
            decimal_places=2,
        )
        record = OrderRecord(
            source_name="bad",
            lines=[
                OrderLine(
                    item_no="BAD-1",
                    product_name="",
                    quantity=Decimal("3"),
                    unit_price=Decimal("2.333"),
                    subtotal=Decimal("8.00"),
                )
            ],
            total_amount=Decimal("9.99"),
        )

        results = validate_order(record, template)

        messages = [issue.message for issue in results.errors + results.warnings]
        self.assertTrue(any("小计金额不一致" in message for message in messages))
        self.assertTrue(any("总金额不一致" in message for message in messages))
        self.assertTrue(any("货号格式不符合规则" in message for message in messages))
        self.assertTrue(any("必填字段缺失: product_name" in message for message in messages))
        self.assertTrue(any("单价小数位数超过 2 位" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
