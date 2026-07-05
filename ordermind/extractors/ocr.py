"""本地 OCR 订单解析器。

OCR 是可选能力：OrderMind 不内置大型 OCR 引擎，而是调用客户电脑上已有的
命令行工具。默认会尝试 `ORDERMIND_OCR_COMMAND`，然后尝试 `tesseract`。
这样文本 PDF、Excel、TXT 仍然零依赖运行；扫描件场景则可以按需安装 OCR。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from ordermind.extractors.text import parse_text_order
from ordermind.models import OrderRecord


DEFAULT_OCR_COMMAND = "tesseract"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
OCR_ENV_VAR = "ORDERMIND_OCR_COMMAND"


class OcrUnavailableError(RuntimeError):
    """当前电脑没有可用 OCR 命令时抛出。"""


def parse_ocr_order(path: str | Path, ocr_command: str | None = None) -> OrderRecord:
    """对图片或扫描件订单执行 OCR，并复用文本订单解析器。"""

    file_path = Path(path)
    text = extract_ocr_text(file_path, ocr_command=ocr_command)
    return parse_text_order(text, source_name=file_path.name)


def extract_ocr_text(path: str | Path, ocr_command: str | None = None) -> str:
    """调用本机 OCR 命令并返回识别文本。"""

    command = _resolve_ocr_command(ocr_command)
    result = subprocess.run(
        _build_ocr_args(command, Path(path)),
        capture_output=True,
        check=False,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ValueError(f"OCR 识别失败: {detail or command}")
    text = result.stdout.strip()
    if not text:
        raise ValueError("OCR 未识别到可用文本")
    return text


def _resolve_ocr_command(ocr_command: str | None = None) -> str:
    """按参数、环境变量、默认命令的顺序寻找 OCR 工具。"""

    command = ocr_command or os.environ.get(OCR_ENV_VAR) or DEFAULT_OCR_COMMAND
    if Path(command).is_file() or shutil.which(command):
        return command
    raise OcrUnavailableError(
        f"OCR 命令不可用: {command}。请安装 Tesseract，或设置 {OCR_ENV_VAR}。"
    )


def _build_ocr_args(command: str, path: Path) -> list[str]:
    """构造 OCR 命令参数。

    Tesseract 使用 `stdout` 作为输出目标；自定义命令只要求接受文件路径并把文本
    写到标准输出，方便后续替换 PaddleOCR、云桌面本地服务或客户自己的工具。
    """

    if Path(command).name.lower().startswith("tesseract"):
        return [command, str(path), "stdout", "-l", "chi_sim+eng"]
    return [command, str(path)]
