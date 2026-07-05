import tempfile
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path

from ordermind.extractors.dispatcher import parse_order_file


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


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


if __name__ == "__main__":
    unittest.main()
