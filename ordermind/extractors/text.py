"""TXT/CSV/TSV 订单解析器。

第一版优先支持结构比较清楚的纯文本和分隔符表格，目标是让产品尽快形成
“上传订单 -> 抽取字段 -> 规则校验”的闭环。复杂 Word/PDF/OCR 会在后续版本
接入更强的文档智能引擎。
"""

from __future__ import annotations

import csv
import re
from decimal import Decimal, InvalidOperation
from io import StringIO

from ordermind.models import Evidence, OrderLine, OrderRecord


HEADER_ALIASES = {
    "item_no": {"货号", "款号", "商品编号", "物料号", "item", "item no", "article no", "sku"},
    "product_name": {"品名", "名称", "产品名称", "商品名称", "description", "product", "name"},
    "quantity": {"数量", "qty", "quantity", "件数"},
    "unit_price": {"单价", "unit price", "price"},
    "subtotal": {"小计", "金额", "小计金额", "amount", "subtotal"},
    "material": {"材质", "材料", "material"},
    "delivery_date": {"交货期", "交期", "delivery", "delivery date"},
    "unit": {"单位", "unit"},
}


def parse_text_order(text: str, source_name: str = "text") -> OrderRecord:
    """解析文本订单。

    解析策略：
    1. 先抽取订单头部字段，例如付款方式、包装要求、交货期、总金额；
    2. 再寻找带逗号或制表符的表格区域；
    3. 根据表头同义词映射到 OrderLine 字段。
    """

    normalized_lines = [line.strip() for line in text.splitlines() if line.strip()]
    record = OrderRecord(source_name=source_name, raw_text=text)
    _extract_header_fields(record, normalized_lines, source_name)
    rows = _extract_csv_like_rows(normalized_lines)
    if rows:
        record.lines.extend(_rows_to_order_lines(rows, source_name))
    if record.total_amount is None:
        record.total_amount = _sum_line_amounts(record.lines)
    if record.total_quantity is None:
        record.total_quantity = _sum_line_quantities(record.lines)
    return record


def _extract_header_fields(record: OrderRecord, lines: list[str], source_name: str) -> None:
    """从普通文本行里抽取订单头字段。

    这里先使用正则表达式处理常见写法。后续可以在这一层加入本地 LLM，
    用于识别“付款条件见附件”这类更自由的表达。
    """

    patterns = {
        "payment_terms": r"(付款方式|付款条件|payment terms?)[:：]\s*(.+)",
        "packaging_requirements": r"(包装要求|包装方式|packing|packaging)[:：]\s*(.+)",
        "delivery_date": r"(交货期|交期|delivery date?)[:：]\s*(.+)",
        "total_amount": r"(总金额|合计金额|订单金额|grand total|total amount|total)[:：]\s*([0-9,]+(?:\.\d+)?)",
        "total_quantity": r"(总数量|合计数量|total quantity|total qty)[:：]\s*([0-9,]+(?:\.\d+)?)",
    }
    for line_no, line in enumerate(lines, start=1):
        for field_name, pattern in patterns.items():
            match = re.search(pattern, line, flags=re.IGNORECASE)
            if not match:
                continue
            value = match.group(2).strip()
            if field_name in {"total_amount", "total_quantity"}:
                setattr(record, field_name, _to_decimal(value))
            else:
                setattr(record, field_name, value)
            record.evidence.append(
                Evidence(source_name=source_name, location=f"line {line_no}", raw_text=line)
            )


def _extract_csv_like_rows(lines: list[str]) -> list[list[str]]:
    """提取 CSV/TSV 风格的表格行。"""

    candidates = [line for line in lines if "," in line or "\t" in line]
    if candidates:
        delimiter = "\t" if sum("\t" in line for line in candidates) > sum("," in line for line in candidates) else ","
        reader = csv.reader(StringIO("\n".join(candidates)), delimiter=delimiter)
        return [[cell.strip() for cell in row] for row in reader if any(cell.strip() for cell in row)]
    return _extract_space_aligned_rows(lines)


def _rows_to_order_lines(rows: list[list[str]], source_name: str) -> list[OrderLine]:
    """把二维表格行转换成订单明细行。"""

    header_index = _find_header_index(rows)
    if header_index is None:
        return []
    headers = rows[header_index]
    data_start_index = header_index + 1
    if header_index + 1 < len(rows):
        merged_headers = _merge_header_rows(headers, rows[header_index + 1])
        if len(_map_headers(merged_headers)) > len(_map_headers(headers)):
            headers = merged_headers
            data_start_index = header_index + 2
    mapping = _map_headers(headers)
    lines: list[OrderLine] = []
    for row_no, row in enumerate(rows[data_start_index:], start=data_start_index + 1):
        if _looks_like_header_row(row) or _looks_like_summary_row(row):
            continue
        line = OrderLine(
            item_no=_cell(row, mapping.get("item_no")),
            product_name=_cell(row, mapping.get("product_name")),
            quantity=_to_decimal(_cell(row, mapping.get("quantity"))),
            unit_price=_to_decimal(_cell(row, mapping.get("unit_price"))),
            subtotal=_to_decimal(_cell(row, mapping.get("subtotal"))),
            material=_cell(row, mapping.get("material")),
            delivery_date=_cell(row, mapping.get("delivery_date")),
            unit=_cell(row, mapping.get("unit")),
            evidence=[
                Evidence(
                    source_name=source_name,
                    location=f"row {row_no}",
                    raw_text=", ".join(row),
                    confidence=0.85,
                )
            ],
        )
        if line.item_no or line.product_name:
            lines.append(line)
    return lines


def _find_header_index(rows: list[list[str]]) -> int | None:
    """在表格中寻找最像表头的一行。

    评分依据是这一行能匹配多少个已知字段别名。至少匹配两个字段才认定为表头，
    避免把普通备注行误判成订单明细表。
    """

    best_index = None
    best_score = 0
    for index, row in enumerate(rows):
        score = len(_map_headers(row))
        if index + 1 < len(rows):
            score = max(score, len(_map_headers(_merge_header_rows(row, rows[index + 1]))))
        if score > best_score:
            best_score = score
            best_index = index
    return best_index if best_score >= 2 else None


def _map_headers(headers: list[str]) -> dict[str, int]:
    """把原始表头映射到标准字段名。"""

    mapping: dict[str, int] = {}
    for index, header in enumerate(headers):
        normalized = _normalize_header(header)
        for field_name, aliases in HEADER_ALIASES.items():
            if field_name in mapping:
                continue
            if any(_header_matches_alias(normalized, _normalize_header(alias)) for alias in aliases):
                mapping[field_name] = index
    return mapping


def _merge_header_rows(top_row: list[str], bottom_row: list[str]) -> list[str]:
    """合并两行拆分表头，例如 `Item` + `No`、`Unit` + `Price`。"""

    width = max(len(top_row), len(bottom_row))
    merged: list[str] = []
    for index in range(width):
        top = _cell(top_row, index)
        bottom = _cell(bottom_row, index)
        if top and bottom:
            merged.append(f"{top} {bottom}")
        else:
            merged.append(top or bottom)
    return merged


def _extract_space_aligned_rows(lines: list[str]) -> list[list[str]]:
    """提取 OCR/PDF 常见的多空格对齐表格。"""

    rows = [
        [cell.strip() for cell in re.split(r"\s{2,}", line.strip()) if cell.strip()]
        for line in lines
        if re.search(r"\s{2,}", line.strip())
    ]
    table_like_rows = [row for row in rows if len(row) >= 3]
    return table_like_rows if len(table_like_rows) >= 2 else []


def _looks_like_header_row(row: list[str]) -> bool:
    """判断一行是否仍像拆分表头，避免把第二行表头当明细。"""

    return len(_map_headers(row)) >= 2


def _normalize_header(value: str) -> str:
    """归一化表头，去掉空格、下划线和大小写差异。"""

    return re.sub(r"[\s_./-]+", "", value.strip().lower())


def _header_matches_alias(normalized_header: str, normalized_alias: str) -> bool:
    """判断表头是否匹配字段别名，兼容 `Order Qty` 这类组合表头。"""

    if not normalized_header or not normalized_alias:
        return False
    if normalized_header == normalized_alias:
        return True
    return len(normalized_alias) >= 3 and normalized_alias in normalized_header


def _cell(row: list[str], index: int | None) -> str:
    """安全读取单元格，列不存在时返回空字符串。"""

    if index is None or index >= len(row):
        return ""
    return row[index].strip()


def _to_decimal(value: str | Decimal | None) -> Decimal | None:
    """把订单中的数字文本转成 Decimal。"""

    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


def _sum_line_amounts(lines: list[OrderLine]) -> Decimal | None:
    """汇总所有明细小计。"""

    values = [line.subtotal for line in lines if line.subtotal is not None]
    if not values:
        return None
    return sum(values, Decimal("0"))


def _sum_line_quantities(lines: list[OrderLine]) -> Decimal | None:
    """汇总所有明细数量。"""

    values = [line.quantity for line in lines if line.quantity is not None]
    if not values:
        return None
    return sum(values, Decimal("0"))


def _looks_like_summary_row(row: list[str]) -> bool:
    """判断一行是否像合计行，合计行不应进入订单明细。"""

    joined = "".join(row).lower()
    return any(keyword in joined for keyword in ["总金额", "合计", "total", "grand total"])
