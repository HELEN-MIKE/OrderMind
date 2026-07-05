"""生成 OrderMind 脱敏仿真订单样例。

样例只能使用虚构公司、联系人、地址和订单号。脚本当前负责生成需要结构化
二进制容器的 XLSX/PDF 文件，文本样例直接维护在 samples/customer_like_orders/ 目录中。
"""

from __future__ import annotations

import html
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "samples" / "customer_like_orders"
OUTPUT = SAMPLE_DIR / "multi_currency_order.xlsx"
PDF_OUTPUT = SAMPLE_DIR / "text_pdf_order.pdf"


def main() -> None:
    """生成可被轻量 XLSX 解析器读取的客户化仿真订单。"""

    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    rows = [
        ["Sanitized Simulation Multi-Currency Order"],
        ["Note", "Fictional entities only; no real customer or supplier data."],
        ["Seller", "Cedar Works Demo Export Co."],
        ["Buyer", "Lakeside Stores Simulation GmbH"],
        ["Order No", "MC-SIM-20260704-004"],
        ["Payment Terms: L/C at sight"],
        ["Packaging: Retail color box plus export carton with fictional mark"],
        ["Delivery Date: 2026-10-08"],
        [],
        ["Item No", "Description", "Qty", "Unit Price", "Amount", "Material", "Unit", "Delivery Date", "Currency Note"],
        ["OM-7101", "Acacia Serving Tray", 300, "12.40", "3720.00", "acacia wood", "PCS", "2026-10-08", "USD"],
        ["OM-7102", "Glass Storage Jar", 520, "7.25", "3770.00", "soda lime glass", "PCS", "2026-10-10", "USD"],
        ["OM-7103", "Linen Table Runner", 190, "13.50", "2565.00", "linen blend", "PCS", "2026-10-12", "USD"],
        ["Total Qty", 1010],
        ["Grand Total", "10055.00"],
    ]
    _write_xlsx(OUTPUT, "Order", rows)
    print(f"created {OUTPUT}")
    pdf_lines = [
        "Sanitized Simulation Text PDF Order",
        "Note: Fictional entities only; no real customer or supplier data.",
        "Seller: Meridian Demo Export Co.",
        "Buyer: Summit Retail Simulation Ltd.",
        "Order No: PDF-SIM-20260704-005",
        "Payment Terms: T/T 30% deposit, 70% balance before shipment",
        "Packaging: 16 PCS per export carton with fictional mark",
        "Delivery Date: 2026-10-22",
        "Item No,Description,Qty,Unit Price,Amount,Material,Unit,Delivery Date",
        "OM-8101,Insulated Food Jar,260,11.20,2912.00,304 stainless steel,PCS,2026-10-22",
        "OM-8102,Silicone Lunch Divider,520,2.10,1092.00,food grade silicone,PCS,2026-10-24",
        "Total Qty: 780",
        "Grand Total: 4004.00",
    ]
    _write_text_pdf(PDF_OUTPUT, pdf_lines)
    print(f"created {PDF_OUTPUT}")


def _write_xlsx(path: Path, sheet_name: str, rows: list[list[Any]]) -> None:
    """写入最小 XLSX 包，避免为样例生成引入运行时依赖。"""

    shared_strings = _SharedStrings()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _root_relationships_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml(sheet_name))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_relationships_xml())
        archive.writestr("xl/worksheets/sheet1.xml", _worksheet_xml(rows, shared_strings))
        archive.writestr("xl/sharedStrings.xml", shared_strings.xml())


def _write_text_pdf(path: Path, lines: list[str]) -> None:
    """写入一个包含可复制文本的最小 PDF 样例。"""

    stream = "BT\n/F1 10 Tf\n72 760 Td\n14 TL\n"
    for index, line in enumerate(lines):
        if index:
            stream += "T*\n"
        stream += f"({_pdf_escape(line)}) Tj\n"
    stream += "ET\n"
    stream_bytes = stream.encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream_bytes)).encode("ascii")
        + b" >>\nstream\n"
        + stream_bytes
        + b"endstream",
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


class _SharedStrings:
    """收集 XLSX sharedStrings，保证文本单元格可被 Excel 和解析器读取。"""

    def __init__(self) -> None:
        self._indexes: dict[str, int] = {}
        self._values: list[str] = []
        self.count = 0

    def index(self, value: Any) -> int:
        self.count += 1
        text = "" if value is None else str(value)
        if text not in self._indexes:
            self._indexes[text] = len(self._values)
            self._values.append(text)
        return self._indexes[text]

    def xml(self) -> str:
        items = "".join(f"<si><t>{html.escape(value)}</t></si>" for value in self._values)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            f'count="{self.count}" uniqueCount="{len(self._values)}">{items}</sst>'
        )


def _worksheet_xml(rows: list[list[Any]], shared_strings: _SharedStrings) -> str:
    row_xml: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells: list[str] = []
        for column_index, value in enumerate(row, start=1):
            if value == "":
                continue
            reference = f"{_column_name(column_index)}{row_index}"
            if isinstance(value, int | float) and not isinstance(value, bool):
                cells.append(f'<c r="{reference}"><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{reference}" t="s"><v>{shared_strings.index(value)}</v></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '</worksheet>'
    )


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        '</Types>'
    )


def _root_relationships_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )


def _workbook_xml(sheet_name: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{html.escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )


def _workbook_relationships_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
        '</Relationships>'
    )


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


if __name__ == "__main__":
    main()
