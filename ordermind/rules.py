"""订单校验规则引擎。

设计原则：
- AI/解析器只负责“识别候选字段”，规则引擎负责“确定性判断”；
- 金额、数量等可计算项必须使用可复现的规则，不能交给大模型自由判断；
- 每条问题保留稳定 code，方便后续做双语展示、筛选统计和报告导出。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from ordermind.models import OrderLine, OrderRecord, ValidationIssue, ValidationReport


@dataclass
class RuleTemplate:
    """可保存、可切换的客户校验模板。

    第一版直接用 JSON 文件保存模板。后续桌面应用可迁移到 SQLite，
    但字段含义保持不变，避免模板配置丢失兼容性。
    """

    name: str
    required_fields: list[str] = field(default_factory=list)
    item_no_pattern: str = ""
    allowed_units: list[str] = field(default_factory=list)
    total_amount_tolerance: Decimal = Decimal("0.01")
    line_amount_tolerance: Decimal = Decimal("0.01")
    decimal_places: int = 2
    spare_ratio: Decimal | None = None
    quantity_tolerance: Decimal | None = None
    material_keywords: list[str] = field(default_factory=list)
    packaging_keywords: list[str] = field(default_factory=list)


def validate_order(record: OrderRecord, template: RuleTemplate) -> ValidationReport:
    """按指定模板校验一份订单。"""

    report = ValidationReport(source_name=record.source_name)
    for index, line in enumerate(record.lines, start=1):
        location = f"line {index}"
        _validate_required_fields(report, line, template.required_fields, location)
        _validate_line_amount(report, line, template, location)
        _validate_item_no(report, line, template, location)
        _validate_unit(report, line, template, location)
        _validate_decimal_places(report, line, template, location)

    _validate_total_amount(report, record, template)
    _validate_total_quantity(report, record, template)
    _validate_header_terms(report, record, template)
    return report


def _validate_required_fields(
    report: ValidationReport,
    line: OrderLine,
    required_fields: list[str],
    location: str,
) -> None:
    """校验每个明细行是否缺少模板要求的字段。"""

    for field_name in required_fields:
        value = getattr(line, field_name, None)
        if value is None or value == "":
            report.add(
                ValidationIssue(
                    severity="error",
                    code="required_missing",
                    message=f"必填字段缺失: {field_name}",
                    location=location,
                )
            )


def _validate_line_amount(
    report: ValidationReport,
    line: OrderLine,
    template: RuleTemplate,
    location: str,
) -> None:
    """校验 `数量 x 单价` 是否等于明细小计。"""

    if line.quantity is None or line.unit_price is None or line.subtotal is None:
        return
    expected = line.quantity * line.unit_price
    difference = abs(expected - line.subtotal)
    if difference > template.line_amount_tolerance:
        report.add(
            ValidationIssue(
                severity="error",
                code="line_amount_mismatch",
                message=f"小计金额不一致: 数量 x 单价 = {expected}, 文件小计 = {line.subtotal}",
                location=location,
            )
        )


def _validate_item_no(
    report: ValidationReport,
    line: OrderLine,
    template: RuleTemplate,
    location: str,
) -> None:
    """校验货号是否符合模板中的正则规则。"""

    if not template.item_no_pattern or not line.item_no:
        return
    if not re.match(template.item_no_pattern, line.item_no):
        report.add(
            ValidationIssue(
                severity="warning",
                code="item_no_format",
                message=f"货号格式不符合规则: {line.item_no}",
                location=location,
            )
        )


def _validate_unit(
    report: ValidationReport,
    line: OrderLine,
    template: RuleTemplate,
    location: str,
) -> None:
    """校验单位是否在模板允许列表中。"""

    if not template.allowed_units or not line.unit:
        return
    if line.unit.upper() not in {unit.upper() for unit in template.allowed_units}:
        report.add(
            ValidationIssue(
                severity="warning",
                code="unit_not_allowed",
                message=f"单位不在允许范围内: {line.unit}",
                location=location,
            )
        )


def _validate_decimal_places(
    report: ValidationReport,
    line: OrderLine,
    template: RuleTemplate,
    location: str,
) -> None:
    """校验单价小数位数，避免客户订单出现不符合财务规则的价格。"""

    if line.unit_price is None:
        return
    exponent = abs(line.unit_price.as_tuple().exponent)
    if exponent > template.decimal_places:
        report.add(
            ValidationIssue(
                severity="warning",
                code="decimal_places",
                message=f"单价小数位数超过 {template.decimal_places} 位: {line.unit_price}",
                location=location,
            )
        )


def _validate_total_amount(
    report: ValidationReport,
    record: OrderRecord,
    template: RuleTemplate,
) -> None:
    """校验文件总金额与明细合计是否一致。"""

    if record.total_amount is None:
        report.add(
            ValidationIssue(
                severity="warning",
                code="total_amount_missing",
                message="总金额缺失，无法进行总金额求和校验",
            )
        )
        return
    computed = record.computed_total_amount()
    difference = abs(computed - record.total_amount)
    if difference > template.total_amount_tolerance:
        report.add(
            ValidationIssue(
                severity="error",
                code="total_amount_mismatch",
                message=f"总金额不一致: 明细合计 = {computed}, 文件总金额 = {record.total_amount}",
            )
        )


def _validate_total_quantity(
    report: ValidationReport,
    record: OrderRecord,
    template: RuleTemplate,
) -> None:
    """校验文件总数量与明细数量合计是否一致。"""

    if record.total_quantity is None:
        return
    computed = record.computed_total_quantity()
    tolerance = template.quantity_tolerance or Decimal("0")
    if abs(computed - record.total_quantity) > tolerance:
        report.add(
            ValidationIssue(
                severity="error",
                code="total_quantity_mismatch",
                message=f"总数量不一致: 明细合计 = {computed}, 文件总数量 = {record.total_quantity}",
            )
        )


def _validate_header_terms(
    report: ValidationReport,
    record: OrderRecord,
    template: RuleTemplate,
) -> None:
    """校验包装、材质等条款关键词。

    第一版先做关键词级别判断。真正的出口合规和检测标准需要客户提供
    规则库后再扩展，不能只靠通用 AI 猜测。
    """

    if template.packaging_keywords and record.packaging_requirements:
        text = record.packaging_requirements
        if not any(keyword in text for keyword in template.packaging_keywords):
            report.add(
                ValidationIssue(
                    severity="warning",
                    code="packaging_keyword_missing",
                    message="包装要求未匹配模板关键词",
                )
            )
    if template.material_keywords:
        materials = " ".join(line.material for line in record.lines)
        if materials and not any(keyword in materials for keyword in template.material_keywords):
            report.add(
                ValidationIssue(
                    severity="warning",
                    code="material_keyword_missing",
                    message="材质未匹配模板关键词",
                )
            )
