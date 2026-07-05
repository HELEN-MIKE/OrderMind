"""生成桌面应用图标资源。

脚本只使用 Python 标准库，方便在干净机器或 CI 上复现图标资源。
生成结果放在 `desktop/resources/`，供 electron-builder 打包 Mac/Windows 应用。
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESOURCES_DIR = ROOT / "desktop" / "resources"
ICONSET_DIR = RESOURCES_DIR / "icon.iconset"


def main() -> int:
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    ICONSET_DIR.mkdir(parents=True, exist_ok=True)

    base_image = _render_icon(1024)
    for filename, size in _mac_icon_sizes().items():
        image = _resize_nearest(base_image, 1024, size)
        (ICONSET_DIR / filename).write_bytes(_png_bytes(size, size, image))

    icon_png = RESOURCES_DIR / "icon.png"
    icon_png.write_bytes(_png_bytes(1024, 1024, base_image))
    _write_ico(RESOURCES_DIR / "icon.ico", base_image)
    _write_icns(RESOURCES_DIR / "icon.icns", base_image)
    print(f"Desktop icons ready: {RESOURCES_DIR}")
    return 0


def _mac_icon_sizes() -> dict[str, int]:
    return {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }


def _render_icon(size: int) -> bytes:
    pixels = bytearray()
    center = (size - 1) / 2
    radius = size * 0.42
    for y in range(size):
        for x in range(size):
            dx = x - center
            dy = y - center
            distance = math.sqrt(dx * dx + dy * dy)
            if distance > radius:
                pixels.extend((0, 0, 0, 0))
                continue

            shade = max(0.0, 1.0 - distance / radius)
            r = int(12 + 28 * shade)
            g = int(103 + 58 * shade)
            b = int(97 + 50 * shade)
            alpha = 255

            if _inside_letter_o(x, y, size) or _inside_letter_m(x, y, size):
                r, g, b = 255, 255, 255
            elif _inside_document_line(x, y, size):
                r, g, b = 184, 227, 216

            pixels.extend((r, g, b, alpha))
    return bytes(pixels)


def _inside_letter_o(x: int, y: int, size: int) -> bool:
    cx = size * 0.34
    cy = size * 0.5
    outer_rx = size * 0.115
    outer_ry = size * 0.165
    inner_rx = size * 0.065
    inner_ry = size * 0.105
    outer = ((x - cx) / outer_rx) ** 2 + ((y - cy) / outer_ry) ** 2 <= 1
    inner = ((x - cx) / inner_rx) ** 2 + ((y - cy) / inner_ry) ** 2 <= 1
    return outer and not inner


def _inside_letter_m(x: int, y: int, size: int) -> bool:
    left = size * 0.48 <= x <= size * 0.54 and size * 0.35 <= y <= size * 0.66
    right = size * 0.67 <= x <= size * 0.73 and size * 0.35 <= y <= size * 0.66
    middle_left = abs((y - size * 0.36) - (x - size * 0.54) * 1.15) <= size * 0.03
    middle_right = abs((y - size * 0.58) + (x - size * 0.62) * 1.15) <= size * 0.03
    vertical_band = size * 0.35 <= y <= size * 0.66 and size * 0.54 <= x <= size * 0.67
    return left or right or (vertical_band and (middle_left or middle_right))


def _inside_document_line(x: int, y: int, size: int) -> bool:
    in_x = size * 0.28 <= x <= size * 0.72
    line_height = size * 0.018
    return in_x and any(abs(y - size * value) <= line_height for value in (0.73, 0.78, 0.83))


def _resize_nearest(pixels: bytes, source_size: int, target_size: int) -> bytes:
    if source_size == target_size:
        return pixels
    output = bytearray()
    for y in range(target_size):
        source_y = int(y * source_size / target_size)
        for x in range(target_size):
            source_x = int(x * source_size / target_size)
            offset = (source_y * source_size + source_x) * 4
            output.extend(pixels[offset : offset + 4])
    return bytes(output)


def _png_bytes(width: int, height: int, pixels: bytes) -> bytes:
    rows = bytearray()
    stride = width * 4
    for y in range(height):
        rows.append(0)
        start = y * stride
        rows.extend(pixels[start : start + stride])
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def _write_ico(path: Path, base_image: bytes) -> None:
    sizes = [16, 32, 48, 64, 128, 256]
    pngs = []
    for size in sizes:
        pixels = _resize_nearest(base_image, 1024, size)
        pngs.append(_png_bytes(size, size, pixels))

    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    directory = bytearray()
    for size, png in zip(sizes, pngs, strict=True):
        size_byte = 0 if size == 256 else size
        directory.extend(struct.pack("<BBBBHHII", size_byte, size_byte, 0, 0, 1, 32, len(png), offset))
        offset += len(png)
    path.write_bytes(header + bytes(directory) + b"".join(pngs))


def _write_icns(path: Path, base_image: bytes) -> None:
    entries = []
    for icon_type, size in (("ic04", 16), ("ic05", 32), ("ic07", 128), ("ic08", 256), ("ic09", 512), ("ic10", 1024)):
        pixels = _resize_nearest(base_image, 1024, size)
        png = _png_bytes(size, size, pixels)
        entries.append(icon_type.encode("ascii") + struct.pack(">I", len(png) + 8) + png)
    body = b"".join(entries)
    path.write_bytes(b"icns" + struct.pack(">I", len(body) + 8) + body)


if __name__ == "__main__":
    raise SystemExit(main())
