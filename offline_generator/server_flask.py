#!/usr/bin/env python3
"""Flask-based API for generating QR codes locally."""
from __future__ import annotations

import argparse
import base64
import io
import math
from typing import Optional

import cairosvg
import ezdxf
from flask import Flask, jsonify, request, Response
from xml.etree import ElementTree as ET
from ezdxf import colors

import segno
SUPPORTED_FORMATS = {"png", "svg", "eps", "pdf", "dxf", "ai"}
MIME_TYPES = {
    "png": "image/png",
    "svg": "image/svg+xml",
    "eps": "application/postscript",
    "pdf": "application/pdf",
    "dxf": "image/vnd.dxf",
    "ai": "application/postscript",
}

DEFAULT_LOGO_MM = 16.5
DEFAULT_QR_MM = 16.5

app = Flask(__name__)


def _decode_logo(data: str) -> bytes:
    if "," in data:
        data = data.split(",", 1)[1]
    return base64.b64decode(data)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _copy_matrix(matrix) -> list[list[int]]:
    return [list(row) for row in matrix]


def _clear_center(matrix: list[list[int]], ratio: float) -> tuple[list[list[int]], tuple[int, int]]:
    if ratio is None or ratio <= 0:
        return matrix, (0, 0)
    size = len(matrix)
    clear_size = max(1, round(size * ratio))
    max_clear = max(1, size - 14)
    if clear_size > max_clear:
        clear_size = max_clear
    # 如果太大會碰到定位點
    clear_size = min(clear_size, max(1, size - 14))
    start = max(0, (size - clear_size) // 2)
    end = min(size, start + clear_size)
    # 確保不超出矩陣
    for r in range(start, end):
        row = matrix[r]
        for c in range(start, end):
            row[c] = 0
    return matrix, (start, end)


def _qr_svg_with_diamond(
    matrix: list[list[int]],
    scale: int,
    border: int,
    dark: str,
    light: str,
) -> str:
    if not light:
        light = "#ffffff"

    def in_finder(row: int, col: int, size: int) -> bool:
        tl = row < 7 and col < 7
        tr = row < 7 and col >= size - 7
        bl = row >= size - 7 and col < 7
        return tl or tr or bl

    def circle_points(cx: float, cy: float, radius: float, segments: int = 80) -> list[tuple[float, float]]:
        return [
            (
                cx + radius * math.cos(2 * math.pi * i / segments),
                cy + radius * math.sin(2 * math.pi * i / segments),
            )
            for i in range(segments)
        ]

    def circle_path(points: list[tuple[float, float]], reverse: bool = False) -> str:
        pts = list(points)
        if reverse:
            pts = pts[::-1]
        path_cmds = [f"M {pts[0][0]} {pts[0][1]}"]
        for i in range(1, len(pts)):
            path_cmds.append(f"L {pts[i][0]} {pts[i][1]}")
        path_cmds.append("Z")
        return " ".join(path_cmds)

    size = len(matrix)
    total = size + border * 2
    svg_w = total * scale
    svg_h = total * scale

    svg_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">',
        # 背景透明，移除白色背景矩形
    ]

    def draw_diamond(x: float, y: float, size_unit: float, fill: str) -> list[str]:
        cx = x + size_unit / 2
        cy = y + size_unit / 2
        half = size_unit / 2
        points = [
            (cx, cy - half),
            (cx + half, cy),
            (cx, cy + half),
            (cx - half, cy),
        ]
        path = " ".join([f"M {points[0][0]} {points[0][1]}"] + [f"L {p[0]} {p[1]}" for p in points[1:]] + ["Z"])
        return [f'<path d="{path}" fill="{fill}"/>']

    # 繪製數據模組（菱形），但跳過定位點區域
    for row in range(size):
        for col in range(size):
            if matrix[row][col] and not in_finder(row, col, size):
                x = (col + border) * scale
                y = (row + border) * scale
                svg_lines.extend(draw_diamond(x, y, scale, dark))

    # 繪製定位點為完整的同心圓
    def draw_finder_pattern(corner_x: float, corner_y: float) -> list[str]:
        """繪製定位點：外圓（黑色）、中圓（透明）、內圓（黑色）"""
        cx = corner_x + 3.5 * scale  # 定位點中心（7x7 區域的中心）
        cy = corner_y + 3.5 * scale
        # 外圓：半徑 3.5 * scale（覆蓋整個 7x7 區域）
        outer_radius = 3.5 * scale
        # 中圓：半徑 2.5 * scale（形成透明環）
        mid_radius = 2.5 * scale
        # 內圓：半徑 1.5 * scale（黑色中心）
        inner_radius = 1.5 * scale
        
        patterns = []
        # 使用 mask 實現透明中環：外圓 + 內圓，中間部分不繪製（透明）
        # 方法：繪製外圓環形（外圓減去中圓）+ 內圓
        outer_pts = circle_points(cx, cy, outer_radius)
        mid_pts = circle_points(cx, cy, mid_radius)
        inner_pts = circle_points(cx, cy, inner_radius)
        
        # 創建外圓環形路徑：外圓（順時針）減去中圓（逆時針）
        # 外圓路徑（順時針）
        outer_path = [f"M {outer_pts[0][0]},{outer_pts[0][1]}"]
        for p in outer_pts[1:]:
            outer_path.append(f"L {p[0]},{p[1]}")
        outer_path.append("Z")
        
        # 中圓路徑（逆時針，用於挖空）
        mid_path = [f"M {mid_pts[0][0]},{mid_pts[0][1]}"]
        for p in reversed(mid_pts[1:]):
            mid_path.append(f"L {p[0]},{p[1]}")
        mid_path.append("Z")
        
        # 組合路徑使用 evenodd 規則：外圓環形（外圓減去中圓）
        combined_d = " ".join(outer_path + mid_path)
        ring_path = f'<path d="{combined_d}" fill="{dark}" fill-rule="evenodd"/>'
        patterns.append(ring_path)
        
        # 內圓（實心黑色）
        inner_path = [f"M {inner_pts[0][0]},{inner_pts[0][1]}"]
        for p in inner_pts[1:]:
            inner_path.append(f"L {p[0]},{p[1]}")
        inner_path.append("Z")
        inner_d = " ".join(inner_path)
        patterns.append(f'<path d="{inner_d}" fill="{dark}"/>')
        return patterns

    # 繪製三個定位點
    # 左上角
    svg_lines.extend(draw_finder_pattern(0 + border, 0 + border))
    # 右上角
    svg_lines.extend(draw_finder_pattern((size - 7) * scale + border, 0 + border))
    # 左下角
    svg_lines.extend(draw_finder_pattern(0 + border, (size - 7) * scale + border))

    svg_lines.append("</svg>")
    return "\n".join(svg_lines)


def _generate_dxf(
    matrix: list[list[int]],
    scale: int,
    border: int,
    dark: str,
    light: str,
) -> bytes:
    import io

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    size = len(matrix)
    dark_rgb = _hex_to_rgb(dark)

    def draw_diamond(x: float, y: float, size_unit: float) -> None:
        cx = x + size_unit / 2
        cy = y + size_unit / 2
        half = size_unit / 2
        points = [
            (cx, cy - half),
            (cx + half, cy),
            (cx, cy + half),
            (cx - half, cy),
            (cx, cy - half),  # 添加第一個點以閉合路徑
        ]
        hatch = msp.add_hatch(color=ezdxf.colors.rgb2int(dark_rgb))
        hatch.paths.add_polyline_path([(p[0], p[1]) for p in points], flags=1)

    def in_finder(row: int, col: int, size: int) -> bool:
        tl = row < 7 and col < 7
        tr = row < 7 and col >= size - 7
        bl = row >= size - 7 and col < 7
        return tl or tr or bl

    def circle_points(cx: float, cy: float, radius: float, segments: int = 80) -> list[tuple[float, float]]:
        return [
            (
                cx + radius * math.cos(2 * math.pi * i / segments),
                cy + radius * math.sin(2 * math.pi * i / segments),
            )
            for i in range(segments)
        ]

    # 繪製數據模組（菱形），但跳過定位點區域
    for row in range(size):
        for col in range(size):
            if matrix[row][col] and not in_finder(row, col, size):
                x = (col + border) * scale
                y = (row + border) * scale
                draw_diamond(x, y, scale)

    # 繪製定位點為完整的同心圓
    def draw_finder_pattern_dxf(corner_x: float, corner_y: float) -> None:
        """繪製定位點：外圓（黑色）、中圓（透明）、內圓（黑色）"""
        cx = corner_x + 3.5 * scale  # 定位點中心（7x7 區域的中心）
        cy = corner_y + 3.5 * scale
        # 外圓：半徑 3.5 * scale（覆蓋整個 7x7 區域）
        outer_radius = 3.5 * scale
        # 中圓：半徑 2.5 * scale（形成透明環，不繪製）
        mid_radius = 2.5 * scale
        # 內圓：半徑 1.5 * scale（黑色中心）
        inner_radius = 1.5 * scale
        
        # 外圓（實心黑色）- 使用填充
        outer_circle_pts = circle_points(cx, cy, outer_radius)
        outer_path = [(p[0], p[1]) for p in outer_circle_pts]
        outer_path.append(outer_path[0])  # 閉合
        hatch_outer = msp.add_hatch(color=ezdxf.colors.rgb2int(dark_rgb))
        hatch_outer.paths.add_polyline_path(outer_path, flags=1)
        
        # 中圓（透明，跳過繪製，形成透明環效果）
        # DXF 格式不支援透明，所以不繪製中圓，讓它保持透明
        
        # 內圓（實心黑色，覆蓋中心）
        inner_circle_pts = circle_points(cx, cy, inner_radius)
        inner_path = [(p[0], p[1]) for p in inner_circle_pts]
        inner_path.append(inner_path[0])  # 閉合
        hatch_inner = msp.add_hatch(color=ezdxf.colors.rgb2int(dark_rgb))
        hatch_inner.paths.add_polyline_path(inner_path, flags=1)

    # 繪製三個定位點
    # 左上角
    draw_finder_pattern_dxf(0 + border, 0 + border)
    # 右上角
    draw_finder_pattern_dxf((size - 7) * scale + border, 0 + border)
    # 左下角
    draw_finder_pattern_dxf(0 + border, (size - 7) * scale + border)

    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def _generate_ai(svg_text: str) -> bytes:
    try:
        eps_bytes = cairosvg.svg2ps(bytestring=svg_text.encode("utf-8"))
        header = b"%!PS-Adobe-3.0\n%%Creator: QR Code Generator\n%%BoundingBox: 0 0 612 792\n%%EndComments\n"
        ai_content = header + eps_bytes + b"\n%%EOF\n"
        return ai_content
    except Exception:
        return svg_text.encode("utf-8")


def _safe_float(value: Optional[float], default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _inject_logo_svg(
    svg_text: str,
    logo_bytes: bytes,
    clear_bounds: tuple[int, int] | None,
    scale: int,
    border: int,
    logo_width_mm: Optional[float],
    logo_height_mm: Optional[float],
) -> str:
    if not clear_bounds:
        return svg_text
    start, end = clear_bounds
    if end <= start:
        return svg_text
    try:
        root = ET.fromstring(svg_text)
        logo_root = ET.fromstring(logo_bytes)
    except ET.ParseError as exc:  # noqa: BLE001
        raise ValueError(f"Logo SVG 解析失敗: {exc}") from exc

    clear_modules = end - start
    clear_units = clear_modules * scale
    target_default_mm = DEFAULT_LOGO_MM
    mm_per_unit = target_default_mm / clear_units if clear_units else None
    width_mm = logo_width_mm or target_default_mm
    height_mm = logo_height_mm or width_mm

    if mm_per_unit:
        width_units = max(1.0, width_mm / mm_per_unit)
        height_units = max(1.0, height_mm / mm_per_unit)
    else:
        width_units = clear_units
        height_units = clear_units

    width_units = min(clear_units, width_units)
    height_units = min(clear_units, height_units)

    offset_units = (start + border) * scale
    x_offset = offset_units + max(0.0, (clear_units - width_units) / 2)
    y_offset = offset_units + max(0.0, (clear_units - height_units) / 2)

    logo_root.set("x", str(x_offset))
    logo_root.set("y", str(y_offset))
    logo_root.set("width", str(width_units))
    logo_root.set("height", str(height_units))
    logo_root.set("preserveAspectRatio", "xMidYMid meet")

    root.append(logo_root)
    return ET.tostring(root, encoding="unicode")


@app.after_request
def add_cors_headers(response: Response) -> Response:
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS, GET"
    return response


@app.route("/preview", methods=["POST", "OPTIONS"])
def preview() -> Response:
    """預覽不同容錯率下的 QR Code 參數，不實際生成 QR Code"""
    if request.method == "OPTIONS":
        return Response(status=204)

    payload = request.get_json(force=True, silent=True) or {}
    text = (payload.get("data") or "").strip()
    if not text:
        return jsonify({"status": "error", "message": "Missing data"}), 400

    scale = int(payload.get("scale", 8))
    border = int(payload.get("border", 0))
    qr_width_mm = _safe_float(payload.get("qrWidthMm"), DEFAULT_QR_MM)
    qr_height_mm = _safe_float(payload.get("qrHeightMm"), qr_width_mm)

    # 不同容錯率的最大 logo 比例
    error_level_max_ratio = {
        "L": 0.07,
        "M": 0.15,
        "Q": 0.25,
        "H": 0.30,
    }

    results = []
    for error_level in ["L", "M", "Q", "H"]:
        try:
            qr = segno.make(text, error=error_level)
            matrix = qr.matrix
            total_modules = len(matrix) + border * 2
            module_size_mm = qr_width_mm / total_modules if total_modules else None

            # 計算不同 logo 比例下的中央留白尺寸
            max_ratio = error_level_max_ratio[error_level]
            matrix_copy, clear_bounds = _clear_center(_copy_matrix(matrix), max_ratio)
            clear_start, clear_end = clear_bounds
            clear_modules = clear_end - clear_start
            clear_size_mm = (
                module_size_mm * clear_modules if module_size_mm and clear_modules > 0 else None
            )

            # 計算該版本的最大容量（以字元數計，使用數字模式可獲得最大容量）
            # 安全地獲取版本號：如果 getattr 返回字符串或無效值，則從模組數計算
            try:
                version_attr = getattr(qr, "version", None)
                if version_attr is None:
                    # 從模組數計算版本號：(modules - 21) / 4 + 1
                    modules = len(matrix)
                    version = (modules - 21) // 4 + 1 if modules >= 21 else 1
                elif isinstance(version_attr, int):
                    version = version_attr
                elif isinstance(version_attr, str):
                    # 嘗試從字符串中提取數字（例如 "M4" -> 4）
                    import re
                    match = re.search(r'\d+', str(version_attr))
                    if match:
                        version = int(match.group())
                    else:
                        modules = len(matrix)
                        version = (modules - 21) // 4 + 1 if modules >= 21 else 1
                else:
                    version = int(version_attr)
            except (ValueError, TypeError, AttributeError):
                # 如果都失敗，從模組數計算
                modules = len(matrix)
                version = (modules - 21) // 4 + 1 if modules >= 21 else 1
            
            max_capacity = None
            if version > 0:
                # QR Code 版本容量表（數字模式，根據容錯率調整）
                # 這些是 QR Code 標準的數字模式容量
                capacity_table = {
                    # L, M, Q, H
                    1: (41, 34, 27, 17), 2: (77, 63, 48, 34), 3: (127, 101, 77, 58), 4: (187, 149, 111, 82),
                    5: (255, 202, 144, 106), 6: (322, 255, 178, 139), 7: (370, 293, 207, 154), 8: (461, 365, 259, 202),
                    9: (552, 432, 312, 235), 10: (652, 513, 364, 288), 11: (772, 604, 427, 331), 12: (883, 691, 489, 374),
                    13: (1022, 796, 580, 427), 14: (1101, 871, 621, 468), 15: (1250, 991, 703, 530), 16: (1408, 1082, 775, 602),
                    17: (1548, 1212, 876, 674), 18: (1725, 1346, 948, 746), 19: (1903, 1500, 1063, 813), 20: (2061, 1600, 1159, 919),
                    21: (2232, 1708, 1224, 969), 22: (2409, 1872, 1358, 1056), 23: (2620, 2059, 1468, 1108), 24: (2812, 2188, 1588, 1228),
                    25: (3057, 2395, 1718, 1286), 26: (3283, 2544, 1804, 1425), 27: (3517, 2701, 1933, 1501), 28: (3669, 2857, 2085, 1581),
                    29: (3909, 3035, 2181, 1677), 30: (4158, 3289, 2358, 1782), 31: (4417, 3486, 2473, 1897), 32: (4686, 3693, 2670, 2022),
                    33: (4965, 3909, 2805, 2157), 34: (5253, 4134, 2949, 2301), 35: (5529, 4343, 3081, 2361), 36: (5836, 4588, 3244, 2524),
                    37: (6153, 4775, 3417, 2625), 38: (6479, 5039, 3599, 2735), 39: (6743, 5313, 3791, 2927), 40: (7089, 5596, 3993, 3057),
                }
                if version in capacity_table:
                    capacities = capacity_table[version]
                    error_index = {"L": 0, "M": 1, "Q": 2, "H": 3}.get(error_level, 0)
                    max_capacity = capacities[error_index]

            results.append({
                "error_level": error_level,
                "version": version,
                "modules_per_side": len(matrix),
                "module_size_mm": module_size_mm,
                "clear_area_mm": clear_size_mm,
                "max_logo_ratio": max_ratio,
                "max_capacity": max_capacity,
            })
        except Exception as exc:  # noqa: BLE001
            results.append({
                "error_level": error_level,
                "error": str(exc),
            })

    return jsonify({
        "status": "ok",
        "data": text,
        "qr_width_mm": qr_width_mm,
        "qr_height_mm": qr_height_mm,
        "preview": results,
    })


@app.route("/generate", methods=["POST", "OPTIONS"])
def generate() -> Response:
    if request.method == "OPTIONS":
        return Response(status=204)

    payload = request.get_json(force=True, silent=True) or {}
    text = (payload.get("data") or "").strip()
    if not text:
        return jsonify({"status": "error", "message": "Missing data"}), 400

    fmt = (payload.get("format") or "png").lower()
    if fmt not in SUPPORTED_FORMATS:
        return jsonify({"status": "error", "message": f"Unsupported format: {fmt}"}), 400

    scale = int(payload.get("scale", 8))
    border = int(payload.get("border", 4))
    dark = payload.get("dark", "#000000")
    light = payload.get("light", "#ffffff")

    error_level = str(payload.get("errorLevel", "L")).upper()
    if error_level not in {"L", "M", "Q", "H"}:
        error_level = "L"

    qr = segno.make(text, error=error_level)

    clear_ratio = _safe_float(payload.get("logoScale"), 0.3)

    matrix = _copy_matrix(qr.matrix)
    matrix, clear_bounds = _clear_center(matrix, clear_ratio)
    svg_text = _qr_svg_with_diamond(matrix, scale, border, dark, light)

    logo_bytes: Optional[bytes] = None
    logo_data: Optional[str] = payload.get("logo")
    if logo_data:
        try:
            logo_bytes = _decode_logo(logo_data)
            if b"<svg" not in logo_bytes.lower():
                raise ValueError("Logo 必須為 SVG 格式")
            logo_width_mm = _safe_float(payload.get("logoWidthMm"), DEFAULT_LOGO_MM)
            logo_height_mm = _safe_float(payload.get("logoHeightMm"), logo_width_mm)
            svg_text = _inject_logo_svg(
                svg_text,
                logo_bytes,
                clear_bounds,
                scale,
                border,
                logo_width_mm,
                logo_height_mm,
            )
        except Exception as exc:  # noqa: BLE001
            return jsonify({"status": "error", "message": f"Logo 處理失敗: {exc}"}), 400

    try:
        if fmt == "svg":
            result_bytes = svg_text.encode("utf-8")
        elif fmt == "png":
            png_bytes = cairosvg.svg2png(bytestring=svg_text.encode("utf-8"))
            result_bytes = png_bytes
        elif fmt == "eps":
            result_bytes = cairosvg.svg2ps(bytestring=svg_text.encode("utf-8"))
        elif fmt == "pdf":
            result_bytes = cairosvg.svg2pdf(bytestring=svg_text.encode("utf-8"))
        elif fmt == "dxf":
            result_bytes = _generate_dxf(matrix, scale, border, dark, light)
        elif fmt == "ai":
            result_bytes = _generate_ai(svg_text)
        else:
            return jsonify({"status": "error", "message": f"Unsupported format: {fmt}"}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"status": "error", "message": f"QR conversion failed: {exc}"}), 500

    b64 = base64.b64encode(result_bytes).decode("ascii")
    filename = payload.get("filename") or f"qrcode.{fmt}"
    total_modules = len(qr.matrix) + border * 2
    qr_width_mm = _safe_float(payload.get("qrWidthMm"), DEFAULT_QR_MM)
    qr_height_mm = _safe_float(payload.get("qrHeightMm"), qr_width_mm)
    module_size_mm = qr_width_mm / total_modules if total_modules else None

    clear_start, clear_end = clear_bounds
    clear_modules = clear_end - clear_start
    clear_size_mm = (
        module_size_mm * clear_modules if module_size_mm and clear_modules > 0 else None
    )

    # 安全地獲取版本號
    try:
        version_attr = getattr(qr, "version", None)
        if version_attr is None:
            modules = len(qr.matrix)
            qr_version = (modules - 21) // 4 + 1 if modules >= 21 else 1
        elif isinstance(version_attr, int):
            qr_version = version_attr
        elif isinstance(version_attr, str):
            import re
            match = re.search(r'\d+', str(version_attr))
            if match:
                qr_version = int(match.group())
            else:
                modules = len(qr.matrix)
                qr_version = (modules - 21) // 4 + 1 if modules >= 21 else 1
        else:
            qr_version = int(version_attr)
    except (ValueError, TypeError, AttributeError):
        modules = len(qr.matrix)
        qr_version = (modules - 21) // 4 + 1 if modules >= 21 else 1

    metadata = {
        "version": qr_version,
        "modules_per_side": len(qr.matrix),
        "module_size": scale,
        "module_size_mm": module_size_mm,
        "qr_width_mm": qr_width_mm,
        "qr_height_mm": qr_height_mm,
        "clear_area_mm": clear_size_mm,
        "logo_width_mm": logo_width_mm if logo_bytes else None,
        "logo_height_mm": logo_height_mm if logo_bytes else None,
    }
    return jsonify({
        "status": "ok",
        "filename": filename,
        "mime": MIME_TYPES[fmt],
        "data": b64,
        "metadata": metadata,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description="Local QR code API server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default 127.0.1)")
    parser.add_argument("--port", type=int, default=5002, help="Port to bind (default 5002)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
