"""订单文件解析分发器。

UI 和 CLI 都只调用 `parse_order_file`，由这里根据扩展名选择具体解析器。
这样后续新增 DOCX/PDF/OCR 时，只需要在这一层增加路由，不影响校验和界面。
"""

from __future__ import annotations

from pathlib import Path

from ordermind.extractors.ocr import IMAGE_SUFFIXES, parse_ocr_order
from ordermind.extractors.pdf import parse_pdf_order
from ordermind.extractors.text import parse_text_order
from ordermind.extractors.xlsx import parse_xlsx_order
from ordermind.models import OrderRecord


def parse_order_file(path: str | Path, ocr_command: str | None = None) -> OrderRecord:
    """解析订单文件，并返回统一的 OrderRecord。"""

    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix in {".txt", ".csv", ".tsv"}:
        return parse_text_order(_read_text(file_path), source_name=file_path.name)
    if suffix in {".xlsx", ".xlsm"}:
        return parse_xlsx_order(file_path)
    if suffix == ".pdf":
        return parse_pdf_order(file_path, ocr_command=ocr_command)
    if suffix in IMAGE_SUFFIXES:
        return parse_ocr_order(file_path, ocr_command=ocr_command)
    raise ValueError(f"暂不支持的文件格式: {suffix}")


def _read_text(path: Path) -> str:
    """用常见中英文编码读取文本文件。"""

    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="ignore")
