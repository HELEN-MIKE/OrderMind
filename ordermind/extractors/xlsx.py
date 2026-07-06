"""轻量 XLSX 解析器。

第一版为了做到“无需安装依赖即可运行”，直接读取 xlsx 内部 XML。
这能覆盖常见电子表格订单，但不是完整 Excel 引擎：
- 不计算公式；
- 不读取复杂样式；
- 只读取第一个工作表；
- 可通过文本解析层恢复常见的多行表头和合并标题行，但不做完整版式还原。

后续生产版本建议接入 openpyxl 或文档智能引擎，并保留本模块作为兜底实现。
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from ordermind.extractors.text import parse_text_order
from ordermind.models import OrderRecord

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def parse_xlsx_order(path: str | Path) -> OrderRecord:
    """解析 XLSX/XLSM 订单文件。"""

    file_path = Path(path)
    rows = read_first_sheet_rows(file_path)
    csv_text = "\n".join(",".join(_escape_cell(cell) for cell in row) for row in rows)
    return parse_text_order(csv_text, source_name=file_path.name)


def read_first_sheet_rows(path: str | Path) -> list[list[str]]:
    """读取第一个工作表为二维字符串数组。"""

    file_path = Path(path)
    with zipfile.ZipFile(file_path) as archive:
        shared_strings = _read_shared_strings(archive)
        sheet_name = _first_sheet_path(archive)
        sheet_xml = archive.read(sheet_name)
    root = ET.fromstring(sheet_xml)
    rows: list[list[str]] = []
    for row_node in root.findall(".//m:sheetData/m:row", NS):
        row_values: dict[int, str] = {}
        for cell_node in row_node.findall("m:c", NS):
            reference = cell_node.attrib.get("r", "")
            index = _column_index(reference)
            row_values[index] = _cell_value(cell_node, shared_strings)
        if row_values:
            max_index = max(row_values)
            rows.append([row_values.get(index, "") for index in range(max_index + 1)])
    return rows


def _read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    """读取 Excel 共享字符串表。

    XLSX 为了节省空间，很多文本单元格会存成 sharedStrings 的索引。
    解析单元格时需要先把索引表读出来。
    """

    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("m:si", NS):
        texts = [node.text or "" for node in item.findall(".//m:t", NS)]
        values.append("".join(texts))
    return values


def _first_sheet_path(archive: zipfile.ZipFile) -> str:
    """找到第一个工作表 XML 路径。"""

    if "xl/worksheets/sheet1.xml" in archive.namelist():
        return "xl/worksheets/sheet1.xml"
    for name in archive.namelist():
        if name.startswith("xl/worksheets/") and name.endswith(".xml"):
            return name
    raise ValueError("未找到 Excel 工作表")


def _cell_value(cell_node: ET.Element, shared_strings: list[str]) -> str:
    """读取单元格文本值。"""

    value_node = cell_node.find("m:v", NS)
    inline_node = cell_node.find(".//m:t", NS)
    if inline_node is not None and inline_node.text:
        return inline_node.text.strip()
    if value_node is None or value_node.text is None:
        return ""
    raw = value_node.text.strip()
    if cell_node.attrib.get("t") == "s":
        index = int(raw)
        return shared_strings[index] if index < len(shared_strings) else ""
    return raw


def _column_index(reference: str) -> int:
    """把 Excel 列号 A/B/AA 转成从 0 开始的列索引。"""

    match = re.match(r"([A-Z]+)", reference)
    if not match:
        return 0
    value = 0
    for char in match.group(1):
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value - 1


def _escape_cell(value: str) -> str:
    """把单元格内容转成安全 CSV 文本，复用文本解析器。"""

    if any(char in value for char in [",", '"', "\n"]):
        return '"' + value.replace('"', '""') + '"'
    return value
