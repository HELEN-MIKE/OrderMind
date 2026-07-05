"""轻量文本型 PDF 订单解析器。

本模块优先覆盖“可复制文字”的电子 PDF。它从 PDF 内容流中提取基础文本操作符，
再复用现有文本订单解析器完成字段抽取。若 PDF 没有可复制文本，会回退到可选
OCR 命令；复杂表格恢复仍属于后续文档智能阶段。
"""

from __future__ import annotations

import re
import zlib
from pathlib import Path

from ordermind.extractors.ocr import parse_ocr_order
from ordermind.extractors.text import parse_text_order
from ordermind.models import OrderRecord


STREAM_RE = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)
TEXT_OBJECT_RE = re.compile(rb"BT(.*?)ET", re.DOTALL)


def parse_pdf_order(path: str | Path, ocr_command: str | None = None) -> OrderRecord:
    """解析文本型 PDF 订单文件。"""

    file_path = Path(path)
    try:
        text = extract_pdf_text(file_path)
    except ValueError:
        return parse_ocr_order(file_path, ocr_command=ocr_command)
    return parse_text_order(text, source_name=file_path.name)


def extract_pdf_text(path: str | Path) -> str:
    """从 PDF 内容流中提取可复制文本。

    这是一个保守的兜底提取器：优先解析未压缩文本流，也尝试 Flate 解压。
    如果文件是扫描件或使用复杂字体编码，可能无法提取到有效文本。
    """

    data = Path(path).read_bytes()
    lines: list[str] = []
    for stream in STREAM_RE.findall(data):
        content = _maybe_decompress(stream.strip())
        for text_object in TEXT_OBJECT_RE.findall(content):
            lines.extend(_extract_text_object_lines(text_object))
    text = "\n".join(line for line in lines if line.strip())
    if not text.strip():
        raise ValueError("未能从 PDF 提取文本，请确认文件不是扫描件或图片 PDF")
    return text


def _maybe_decompress(stream: bytes) -> bytes:
    """尝试解压 PDF Flate 内容流，失败时按原始流处理。"""

    try:
        return zlib.decompress(stream)
    except zlib.error:
        return stream


def _extract_text_object_lines(content: bytes) -> list[str]:
    """提取一个 BT/ET 文本对象里的文本行。"""

    lines: list[str] = []
    current = ""
    index = 0
    while index < len(content):
        char = content[index:index + 1]
        if char == b"(":
            value, index = _read_literal_string(content, index + 1)
            current += value
            continue
        if char == b"<" and content[index:index + 2] != b"<<":
            value, index = _read_hex_string(content, index + 1)
            current += value
            continue
        if content.startswith(b"T*", index):
            lines.append(current)
            current = ""
            index += 2
            continue
        if content.startswith(b"'", index):
            lines.append(current)
            current = ""
            index += 1
            continue
        if content[index:index + 1] in {b"\r", b"\n"}:
            previous_token = _previous_operator(content[:index])
            if previous_token in {b"Tj", b"TJ", b"'", b'"'} and current:
                lines.append(current)
                current = ""
        index += 1
    if current:
        lines.append(current)
    return lines


def _read_literal_string(content: bytes, index: int) -> tuple[str, int]:
    """读取 PDF 圆括号字符串，处理常见转义。"""

    output = bytearray()
    depth = 1
    while index < len(content) and depth:
        char = content[index]
        if char == 92:  # backslash
            index += 1
            if index >= len(content):
                break
            escaped = content[index]
            replacements = {
                ord("n"): b"\n",
                ord("r"): b"\r",
                ord("t"): b"\t",
                ord("b"): b"\b",
                ord("f"): b"\f",
                ord("("): b"(",
                ord(")"): b")",
                ord("\\"): b"\\",
            }
            output.extend(replacements.get(escaped, bytes([escaped])))
        elif char == ord("("):
            depth += 1
            output.append(char)
        elif char == ord(")"):
            depth -= 1
            if depth:
                output.append(char)
        else:
            output.append(char)
        index += 1
    return _decode_pdf_bytes(bytes(output)), index


def _read_hex_string(content: bytes, index: int) -> tuple[str, int]:
    """读取 PDF 尖括号十六进制字符串。"""

    end = content.find(b">", index)
    if end == -1:
        return "", len(content)
    raw = re.sub(rb"\s+", b"", content[index:end])
    if len(raw) % 2:
        raw += b"0"
    try:
        decoded = bytes.fromhex(raw.decode("ascii"))
    except ValueError:
        decoded = b""
    return _decode_pdf_bytes(decoded), end + 1


def _previous_operator(content: bytes) -> bytes:
    """返回当前位置前最后一个 PDF 操作符 token。"""

    tokens = re.findall(rb"[A-Za-z*'\"]+", content)
    return tokens[-1] if tokens else b""


def _decode_pdf_bytes(value: bytes) -> str:
    """按 PDF 常见编码顺序解码文本。"""

    if value.startswith(b"\xfe\xff"):
        return value[2:].decode("utf-16-be", errors="ignore")
    for encoding in ("utf-8", "latin-1"):
        try:
            return value.decode(encoding)
        except UnicodeDecodeError:
            continue
    return value.decode(errors="ignore")
