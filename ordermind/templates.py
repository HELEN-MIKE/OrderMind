"""规则模板读写。

模板使用 JSON 是为了让业务人员和实施人员都能看懂、能备份、能版本管理。
金额容差、数量容差等字段在 JSON 中保存为字符串，读取时转换为 Decimal，
避免浮点数精度影响校验结果。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from ordermind.rules import RuleTemplate


DECIMAL_FIELDS = {
    "total_amount_tolerance",
    "line_amount_tolerance",
    "spare_ratio",
    "quantity_tolerance",
}


def load_template(path: str | Path) -> RuleTemplate:
    """从 JSON 文件读取规则模板。"""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for field_name in DECIMAL_FIELDS:
        if data.get(field_name) is not None:
            data[field_name] = Decimal(str(data[field_name]))
    return RuleTemplate(**data)


def save_template(template: RuleTemplate, path: str | Path) -> None:
    """把规则模板保存为 JSON。"""

    data = asdict(template)
    Path(path).write_text(
        json.dumps(_json_ready(data), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _json_ready(value: Any) -> Any:
    """把包含 Decimal 的数据结构转换成 JSON 可序列化结构。"""

    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value
