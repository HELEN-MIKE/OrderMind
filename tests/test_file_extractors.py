import tempfile
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path

from ordermind.extractors.dispatcher import parse_order_file
from ordermind.extractors.ocr import OcrUnavailableError


class FileExtractorsTest(unittest.TestCase):
    def test_parse_xlsx_order_extracts_rows_from_first_sheet(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "order.xlsx"
            _write_minimal_xlsx(path)

            record = parse_order_file(path)

        self.assertEqual(record.source_name, "order.xlsx")
        self.assertEqual(len(record.lines), 2)
        self.assertEqual(record.lines[0].item_no, "OM-2001")
        self.assertEqual(record.lines[0].product_name, "玻璃杯")
        self.assertEqual(record.lines[1].quantity, Decimal("50"))
        self.assertEqual(record.total_amount, Decimal("400.00"))

    def test_parse_complex_xlsx_recovers_merged_header_and_multiline_labels(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "complex.xlsx"
            _write_complex_xlsx(path)

            record = parse_order_file(path)

        self.assertEqual(record.source_name, "complex.xlsx")
        self.assertEqual(len(record.lines), 2)
        self.assertEqual(record.lines[0].item_no, "OM-3101")
        self.assertEqual(record.lines[0].product_name, "Vacuum Bottle")
        self.assertEqual(record.lines[0].material, "304 stainless steel")
        self.assertEqual(record.lines[1].quantity, Decimal("60"))
        self.assertEqual(record.total_amount, Decimal("1170.00"))

    def test_parse_space_aligned_text_table_recovers_order_lines(self):
        text = """OCR text table
Item No     Description       Qty   Unit Price   Amount    Material
OM-7101     Travel Mug        40    8.50         340.00    stainless steel
OM-7102     Gift Box          40    1.20         48.00     kraft paper
Grand Total: 388.00
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "space-table.txt"
            path.write_text(text, encoding="utf-8")

            record = parse_order_file(path)

        self.assertEqual(len(record.lines), 2)
        self.assertEqual(record.lines[0].item_no, "OM-7101")
        self.assertEqual(record.lines[0].product_name, "Travel Mug")
        self.assertEqual(record.lines[1].material, "kraft paper")
        self.assertEqual(record.total_amount, Decimal("388.00"))

    def test_parse_text_pdf_order_extracts_lines_from_content_stream(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "order.pdf"
            _write_minimal_text_pdf(path)

            record = parse_order_file(path)

        self.assertEqual(record.source_name, "order.pdf")
        self.assertEqual(len(record.lines), 2)
        self.assertEqual(record.lines[0].item_no, "OM-8001")
        self.assertEqual(record.lines[0].product_name, "Steel Lunch Box")
        self.assertEqual(record.lines[1].quantity, Decimal("80"))
        self.assertEqual(record.total_amount, Decimal("1738.00"))
        self.assertEqual(record.payment_terms, "T/T 30% deposit, balance before shipment")

    def test_parse_image_order_uses_optional_ocr_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "scan.png"
            image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
            ocr_command = _write_fake_ocr_command(Path(tmpdir))

            record = parse_order_file(image_path, ocr_command=str(ocr_command))

        self.assertEqual(record.source_name, "scan.png")
        self.assertEqual(len(record.lines), 1)
        self.assertEqual(record.lines[0].item_no, "OM-9001")
        self.assertEqual(record.lines[0].product_name, "OCR Cup")
        self.assertEqual(record.total_amount, Decimal("25.00"))

    def test_parse_scanned_pdf_falls_back_to_optional_ocr_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "scanned.pdf"
            _write_image_only_pdf(pdf_path)
            ocr_command = _write_fake_ocr_command(Path(tmpdir))

            record = parse_order_file(pdf_path, ocr_command=str(ocr_command))

        self.assertEqual(record.source_name, "scanned.pdf")
        self.assertEqual(len(record.lines), 1)
        self.assertEqual(record.lines[0].item_no, "OM-9001")
        self.assertEqual(record.total_amount, Decimal("25.00"))

    def test_parse_image_order_reports_when_ocr_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "scan.jpg"
            image_path.write_bytes(b"not a real jpeg")

            with self.assertRaises(OcrUnavailableError) as context:
                parse_order_file(image_path, ocr_command="missing-ordermind-ocr")

        self.assertIn("OCR", str(context.exception))
        self.assertIn("missing-ordermind-ocr", str(context.exception))


def _write_minimal_xlsx(path: Path) -> None:
    files = {
        "[Content_Types].xml": """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>
""",
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
""",
        "xl/workbook.xml": """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="订单" sheetId="1" r:id="rId1"/></sheets>
</workbook>
""",
        "xl/_rels/workbook.xml.rels": """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>
</Relationships>
""",
        "xl/sharedStrings.xml": """<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="15" uniqueCount="15">
  <si><t>客户订单</t></si>
  <si><t>货号</t></si>
  <si><t>品名</t></si>
  <si><t>数量</t></si>
  <si><t>单价</t></si>
  <si><t>小计</t></si>
  <si><t>材质</t></si>
  <si><t>OM-2001</t></si>
  <si><t>玻璃杯</t></si>
  <si><t>高硼硅玻璃</t></si>
  <si><t>OM-2002</t></si>
  <si><t>杯盖</t></si>
  <si><t>硅胶</t></si>
  <si><t>总金额</t></si>
  <si><t>400.00</t></si>
</sst>
""",
        "xl/worksheets/sheet1.xml": """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1"><c r="A1" t="s"><v>0</v></c></row>
    <row r="2">
      <c r="A2" t="s"><v>1</v></c><c r="B2" t="s"><v>2</v></c><c r="C2" t="s"><v>3</v></c>
      <c r="D2" t="s"><v>4</v></c><c r="E2" t="s"><v>5</v></c><c r="F2" t="s"><v>6</v></c>
    </row>
    <row r="3">
      <c r="A3" t="s"><v>7</v></c><c r="B3" t="s"><v>8</v></c><c r="C3"><v>100</v></c>
      <c r="D3"><v>2.5</v></c><c r="E3"><v>250.00</v></c><c r="F3" t="s"><v>9</v></c>
    </row>
    <row r="4">
      <c r="A4" t="s"><v>10</v></c><c r="B4" t="s"><v>11</v></c><c r="C4"><v>50</v></c>
      <c r="D4"><v>3</v></c><c r="E4"><v>150.00</v></c><c r="F4" t="s"><v>12</v></c>
    </row>
    <row r="5"><c r="D5" t="s"><v>13</v></c><c r="E5" t="s"><v>14</v></c></row>
  </sheetData>
  <mergeCells count="1"><mergeCell ref="A1:F1"/></mergeCells>
</worksheet>
""",
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def _write_complex_xlsx(path: Path) -> None:
    files = {
        "[Content_Types].xml": """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>
""",
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
""",
        "xl/workbook.xml": """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="客户乱格式订单" sheetId="1" r:id="rId1"/></sheets>
</workbook>
""",
        "xl/_rels/workbook.xml.rels": """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>
</Relationships>
""",
        "xl/sharedStrings.xml": """<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="22" uniqueCount="22">
  <si><t>Customer Draft PO</t></si>
  <si><t>Remark: merged title and two-row header should not block parsing</t></si>
  <si><t>Item</t></si>
  <si><t>Product</t></si>
  <si><t>Material</t></si>
  <si><t>Order</t></si>
  <si><t>Unit</t></si>
  <si><t>Line</t></si>
  <si><t>No</t></si>
  <si><t>Name</t></si>
  <si><t></t></si>
  <si><t>Qty</t></si>
  <si><t>Price</t></si>
  <si><t>Amount</t></si>
  <si><t>OM-3101</t></si>
  <si><t>Vacuum Bottle</t></si>
  <si><t>304 stainless steel</t></si>
  <si><t>OM-3102</t></si>
  <si><t>Replacement Lid</t></si>
  <si><t>PP</t></si>
  <si><t>Grand Total</t></si>
  <si><t>1170.00</t></si>
</sst>
""",
        "xl/worksheets/sheet1.xml": """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1"><c r="A1" t="s"><v>0</v></c></row>
    <row r="2"><c r="A2" t="s"><v>1</v></c></row>
    <row r="3">
      <c r="A3" t="s"><v>2</v></c><c r="B3" t="s"><v>3</v></c><c r="C3" t="s"><v>4</v></c>
      <c r="D3" t="s"><v>5</v></c><c r="E3" t="s"><v>6</v></c><c r="F3" t="s"><v>7</v></c>
    </row>
    <row r="4">
      <c r="A4" t="s"><v>8</v></c><c r="B4" t="s"><v>9</v></c>
      <c r="D4" t="s"><v>11</v></c><c r="E4" t="s"><v>12</v></c><c r="F4" t="s"><v>13</v></c>
    </row>
    <row r="5">
      <c r="A5" t="s"><v>14</v></c><c r="B5" t="s"><v>15</v></c><c r="C5" t="s"><v>16</v></c>
      <c r="D5"><v>100</v></c><c r="E5"><v>9.9</v></c><c r="F5"><v>990.00</v></c>
    </row>
    <row r="6">
      <c r="A6" t="s"><v>17</v></c><c r="B6" t="s"><v>18</v></c><c r="C6" t="s"><v>19</v></c>
      <c r="D6"><v>60</v></c><c r="E6"><v>3</v></c><c r="F6"><v>180.00</v></c>
    </row>
    <row r="7"><c r="E7" t="s"><v>20</v></c><c r="F7" t="s"><v>21</v></c></row>
  </sheetData>
  <mergeCells count="2">
    <mergeCell ref="A1:F1"/>
    <mergeCell ref="A2:F2"/>
  </mergeCells>
</worksheet>
""",
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def _write_minimal_text_pdf(path: Path) -> None:
    lines = [
        "Sanitized Simulation PDF Order",
        "Payment Terms: T/T 30% deposit, balance before shipment",
        "Packaging: 20 PCS per export carton",
        "Delivery Date: 2026-10-18",
        "Item No,Description,Qty,Unit Price,Amount,Material,Unit,Delivery Date",
        "OM-8001,Steel Lunch Box,120,9.15,1098.00,stainless steel,PCS,2026-10-18",
        "OM-8002,Silicone Seal Ring,80,8.00,640.00,food grade silicone,PCS,2026-10-20",
        "Total Qty: 200",
        "Grand Total: 1738.00",
    ]
    stream = "BT\n/F1 10 Tf\n72 760 Td\n"
    for index, line in enumerate(lines):
        if index:
            stream += "T*\n"
        stream += f"({_pdf_escape(line)}) Tj\n"
    stream += "ET\n"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n"
            f"{stream}endstream"
        ).encode("latin-1"),
    ]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode("latin-1"))
        content.extend(obj)
        content.extend(b"\nendobj\n")
    xref_offset = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    content.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("latin-1")
    )
    path.write_bytes(bytes(content))


def _write_image_only_pdf(path: Path) -> None:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources << >> /Contents 4 0 R >>",
        b"<< /Length 0 >>\nstream\n\nendstream",
    ]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode("latin-1"))
        content.extend(obj)
        content.extend(b"\nendobj\n")
    xref_offset = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    content.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("latin-1")
    )
    path.write_bytes(bytes(content))


def _write_fake_ocr_command(directory: Path) -> Path:
    command = directory / "fake_ocr.py"
    command.write_text(
        """#!/usr/bin/env python3
import sys

sys.stdout.write(\"\"\"Simulated OCR Order
Item No,Description,Qty,Unit Price,Amount,Material,Unit,Delivery Date
OM-9001,OCR Cup,10,2.50,25.00,glass,PCS,2026-11-01
Grand Total: 25.00
\"\"\")
""",
        encoding="utf-8",
    )
    command.chmod(0o755)
    return command


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


if __name__ == "__main__":
    unittest.main()
