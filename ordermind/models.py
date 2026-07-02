"""OrderMind 的领域数据模型。

本模块只定义数据结构，不做文件解析、AI 判断或规则校验。
这样做的目的有两个：
1. 让 TXT/XLSX/DOCX/PDF 等不同来源先转换成同一套订单结构；
2. 让校验规则只依赖稳定模型，后续替换解析算法时不会影响校验层。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class Evidence:
    """字段来源证据。

    每个自动识别出来的字段都应该尽量带上来源位置。真实审单场景里，
    用户不会盲信 AI 结果，因此“这个值来自哪里”比单纯给出值更重要。
    """

    source_name: str
    location: str
    raw_text: str = ""
    confidence: float = 1.0


@dataclass
class OrderLine:
    """订单明细行。

    所有金额和数量使用 Decimal，避免 float 在金额验算中出现二进制精度误差。
    字段默认允许为空，因为第一版需要支持“不完整识别 + 人工确认”的流程。
    """

    item_no: str = ""
    product_name: str = ""
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    subtotal: Decimal | None = None
    material: str = ""
    delivery_date: str = ""
    unit: str = ""
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class OrderRecord:
    """一次订单解析后的结构化结果。"""

    source_name: str
    lines: list[OrderLine] = field(default_factory=list)
    total_amount: Decimal | None = None
    total_quantity: Decimal | None = None
    delivery_date: str = ""
    payment_terms: str = ""
    packaging_requirements: str = ""
    compliance_terms: str = ""
    raw_text: str = ""
    evidence: list[Evidence] = field(default_factory=list)

    def computed_total_amount(self) -> Decimal:
        """按明细行重新计算总金额。

        优先使用文件里识别出的明细小计；如果小计缺失但数量和单价存在，
        则现场计算 `数量 * 单价`。这能覆盖一部分客户订单没有小计列的情况。
        """

        total = Decimal("0")
        for line in self.lines:
            if line.subtotal is not None:
                total += line.subtotal
            elif line.quantity is not None and line.unit_price is not None:
                total += line.quantity * line.unit_price
        return total

    def computed_total_quantity(self) -> Decimal:
        """按明细行汇总数量，用于总数量求和校验。"""

        total = Decimal("0")
        for line in self.lines:
            if line.quantity is not None:
                total += line.quantity
        return total


@dataclass
class ValidationIssue:
    """单条校验问题。severity 取值为 error / warning / info。"""

    severity: str
    code: str
    message: str
    location: str = ""


@dataclass
class ValidationReport:
    """一次订单校验的完整问题清单。"""

    source_name: str
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    infos: list[ValidationIssue] = field(default_factory=list)

    def add(self, issue: ValidationIssue) -> None:
        """按严重级别把问题放入对应列表，方便 UI 分栏展示。"""

        if issue.severity == "error":
            self.errors.append(issue)
        elif issue.severity == "warning":
            self.warnings.append(issue)
        else:
            self.infos.append(issue)
