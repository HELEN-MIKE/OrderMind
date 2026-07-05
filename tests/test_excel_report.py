import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

from ordermind.reporting import payload_to_xlsx


class ExcelReportTest(unittest.TestCase):
    def test_payload_to_xlsx_creates_a_readable_multi_sheet_workbook(self):
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
                        "delivery_date": "2026-08-15",
                        "unit": "PCS",
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

        workbook_bytes = payload_to_xlsx(payload, lang="zh")

        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.xlsx"
            path.write_bytes(workbook_bytes)
            with zipfile.ZipFile(path) as workbook:
                names = set(workbook.namelist())
                self.assertIn("xl/workbook.xml", names)
                self.assertIn("xl/worksheets/sheet1.xml", names)
                self.assertIn("xl/worksheets/sheet2.xml", names)
                self.assertIn("xl/worksheets/sheet3.xml", names)
                self.assertIn("xl/worksheets/sheet4.xml", names)

                workbook_xml = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
                ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                sheet_names = [
                    sheet.attrib["name"]
                    for sheet in workbook_xml.findall("main:sheets/main:sheet", ns)
                ]

                shared_strings = workbook.read("xl/sharedStrings.xml").decode("utf-8")

        self.assertEqual(sheet_names, ["摘要", "订单明细", "校验问题", "结构化JSON"])
        self.assertIn("sample_order.txt", shared_strings)
        self.assertIn("OM-1001", shared_strings)
        self.assertIn("需要人工复核", shared_strings)


if __name__ == "__main__":
    unittest.main()
