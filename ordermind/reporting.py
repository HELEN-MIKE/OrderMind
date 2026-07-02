"""审单结果输出工具。

解析和校验完成后，UI、CLI、后续桌面应用都需要同一份结构化结果。
本模块负责把内部 dataclass 转成 JSON/CSV 可输出格式。
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from decimal import Decimal
from io import StringIO
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
