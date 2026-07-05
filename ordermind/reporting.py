"""审单结果输出工具。

解析和校验完成后，UI、CLI、后续桌面应用都需要同一份结构化结果。
本模块负责把内部 dataclass 转成 JSON/CSV 可输出格式。
"""

from __future__ import annotations

import csv
import json
import zipfile
from dataclasses import asdict
from decimal import Decimal
from io import BytesIO, StringIO
from typing import Any

from ordermind.models import OrderRecord, ValidationReport


def record_to_dict(record: OrderRecord) -> dict[str, Any]:
    """把订单记录转换成普通 dict。"""

    return _json_ready(asdict(record))


def report_to_dict(report: ValidationReport) -> dict[str, Any]:
    """把校验报告转换成普通 dict。"""

    return _json_ready(asdict(report))


def build_result_payload(record: OrderRecord, report: ValidationReport) -> dict[str, Any]:
    """组装 UI 和 CLI 共用的结果 payload。"""

    return {
        "record": record_to_dict(record),
        "report": report_to_dict(report),
        "summary": {
            "line_count": len(record.lines),
            "error_count": len(report.errors),
            "warning_count": len(report.warnings),
            "info_count": len(report.infos),
        },
    }


def payload_to_json(payload: dict[str, Any]) -> str:
    """把结果 payload 输出为可读 JSON。"""

    return json.dumps(payload, ensure_ascii=False, indent=2)


def payload_to_xlsx(payload: dict[str, Any], lang: str = "zh") -> bytes:
    """把审单结果导出为 Excel 2007+ `.xlsx` 工作簿。

    为了保持桌面包离线无依赖，这里直接写最小 OpenXML 工作簿。
    工作簿包含摘要、订单明细、校验问题和结构化 JSON 四个工作表。
    """

    del lang  # 预留给后续英文列名；当前客户验收优先使用中文表头。
    record = payload["record"]
    report = payload["report"]
    summary = payload["summary"]
    issues = report.get("errors", []) + report.get("warnings", []) + report.get("infos", [])
    sheets = [
        (
            "摘要",
            [
                ["项目", "值"],
                ["来源文件", record.get("source_name", "")],
                ["明细行", summary.get("line_count", 0)],
                ["错误", summary.get("error_count", 0)],
                ["警告", summary.get("warning_count", 0)],
                ["提示", summary.get("info_count", 0)],
            ],
        ),
        (
            "订单明细",
            [
                ["货号", "品名", "数量", "单价", "小计", "材质", "交货期", "单位"],
                *[
                    [
                        line.get("item_no", ""),
                        line.get("product_name", ""),
                        line.get("quantity", ""),
                        line.get("unit_price", ""),
                        line.get("subtotal", ""),
                        line.get("material", ""),
                        line.get("delivery_date", ""),
                        line.get("unit", ""),
                    ]
                    for line in record.get("lines", [])
                ],
            ],
        ),
        (
            "校验问题",
            [
                ["级别", "代码", "位置", "问题"],
                *[
                    [
                        issue.get("severity", ""),
                        issue.get("code", ""),
                        issue.get("location", ""),
                        issue.get("message", ""),
                    ]
                    for issue in issues
                ],
            ],
        ),
        (
            "结构化JSON",
            [["JSON"], *[[line] for line in payload_to_json(payload).splitlines()]],
        ),
    ]
    return _build_xlsx(sheets)


def lines_to_csv(record: OrderRecord) -> str:
    """导出订单明细 CSV。"""

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["货号", "品名", "数量", "单价", "小计", "材质", "交货期", "单位"])
    for line in record.lines:
        writer.writerow(
            [
                line.item_no,
                line.product_name,
                _stringify(line.quantity),
                _stringify(line.unit_price),
                _stringify(line.subtotal),
                line.material,
                line.delivery_date,
                line.unit,
            ]
        )
    return output.getvalue()


def issues_to_csv(report: ValidationReport) -> str:
    """导出问题清单 CSV。"""

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["级别", "代码", "位置", "问题"])
    for issue in report.errors + report.warnings + report.infos:
        writer.writerow([issue.severity, issue.code, issue.location, issue.message])
    return output.getvalue()


def _json_ready(value: Any) -> Any:
    """递归转换 Decimal 等非 JSON 原生类型。"""

    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def _stringify(value: Any) -> str:
    """把空值和 Decimal 转成适合 CSV 的字符串。"""

    return "" if value is None else str(value)


def _build_xlsx(sheets: list[tuple[str, list[list[Any]]]]) -> bytes:
    """写入一个最小但可由 Excel/Numbers/LibreOffice 打开的 xlsx。"""

    shared_strings = _SharedStrings()
    sheet_xml = [
        _worksheet_xml(rows, shared_strings)
        for _, rows in sheets
    ]
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as workbook:
        workbook.writestr("[Content_Types].xml", _content_types_xml(len(sheets)))
        workbook.writestr("_rels/.rels", _root_relationships_xml())
        workbook.writestr("xl/workbook.xml", _workbook_xml([name for name, _ in sheets]))
        workbook.writestr("xl/_rels/workbook.xml.rels", _workbook_relationships_xml(len(sheets)))
        workbook.writestr("xl/styles.xml", _styles_xml())
        workbook.writestr("xl/sharedStrings.xml", shared_strings.xml())
        for index, xml in enumerate(sheet_xml, start=1):
            workbook.writestr(f"xl/worksheets/sheet{index}.xml", xml)
    return buffer.getvalue()


class _SharedStrings:
    """收集并复用 Excel sharedStrings。"""

    def __init__(self) -> None:
        self._indexes: dict[str, int] = {}
        self._values: list[str] = []
        self.count = 0

    def index(self, value: Any) -> int:
        self.count += 1
        text = _stringify(value)
        if text not in self._indexes:
            self._indexes[text] = len(self._values)
            self._values.append(text)
        return self._indexes[text]

    def xml(self) -> str:
        items = "".join(
            f"<si><t>{_xml_escape(value)}</t></si>"
            for value in self._values
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            f'count="{self.count}" uniqueCount="{len(self._values)}">{items}</sst>'
        )


def _worksheet_xml(rows: list[list[Any]], shared_strings: _SharedStrings) -> str:
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            reference = f"{_column_name(column_index)}{row_index}"
            style = ' s="1"' if row_index == 1 else ""
            if isinstance(value, int | float) and not isinstance(value, bool):
                cells.append(f'<c r="{reference}"{style}><v>{value}</v></c>')
            else:
                string_index = shared_strings.index(value)
                cells.append(f'<c r="{reference}" t="s"{style}><v>{string_index}</v></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" state="frozen"/></sheetView></sheetViews>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '</worksheet>'
    )


def _content_types_xml(sheet_count: int) -> str:
    sheets = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        f"{sheets}</Types>"
    )


def _root_relationships_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )


def _workbook_xml(sheet_names: list[str]) -> str:
    sheets = "".join(
        f'<sheet name="{_xml_escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(sheet_names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheets}</sheets></workbook>"
    )


def _workbook_relationships_xml(sheet_count: int) -> str:
    relationships = [
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, sheet_count + 1)
    ]
    relationships.append(
        f'<Relationship Id="rId{sheet_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )
    relationships.append(
        f'<Relationship Id="rId{sheet_count + 2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{"".join(relationships)}</Relationships>'
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
        '</styleSheet>'
    )


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
