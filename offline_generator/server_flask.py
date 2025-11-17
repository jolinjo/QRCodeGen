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
    logo_bytes: Optional[bytes] = None,
    clear_bounds: Optional[tuple[int, int]] = None,
    logo_width_mm: Optional[float] = None,
    logo_height_mm: Optional[float] = None,
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
        # 中圓：半徑 2.5 * scale（形成透明環）
        mid_radius = 2.5 * scale
        # 內圓：半徑 1.5 * scale（黑色中心）
        inner_radius = 1.5 * scale
        
        # 創建外圓環形（外圓減去中圓）- 使用 hatch 的邊界路徑創建環形
        outer_circle_pts = circle_points(cx, cy, outer_radius)
        mid_circle_pts = circle_points(cx, cy, mid_radius)
        
        # 外圓路徑（順時針，flags=0 表示外邊界）
        outer_path = [(p[0], p[1]) for p in outer_circle_pts]
        outer_path.append(outer_path[0])  # 閉合
        
        # 中圓路徑（逆時針，flags=1 表示內邊界/挖空）
        mid_path = [(p[0], p[1]) for p in reversed(mid_circle_pts)]
        mid_path.append(mid_path[0])  # 閉合
        
        # 創建環形填充（外圓 - 中圓）
        hatch_ring = msp.add_hatch(color=ezdxf.colors.rgb2int(dark_rgb))
        hatch_ring.paths.add_polyline_path(outer_path, flags=0)  # 外邊界
        hatch_ring.paths.add_polyline_path(mid_path, flags=1)    # 內邊界（挖空）
        
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

    # 繪製 logo（如果有）
    if logo_bytes and clear_bounds:
        try:
            _add_logo_to_dxf(
                msp,
                logo_bytes,
                clear_bounds,
                scale,
                border,
                logo_width_mm,
                logo_height_mm,
                dark_rgb,
                size,
            )
        except Exception as exc:  # noqa: BLE001
            # 如果 logo 處理失敗，跳過繼續生成 DXF
            # 記錄錯誤但不中斷 DXF 生成
            import sys
            print(f"DXF Logo processing error: {exc}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            pass

    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def _add_logo_to_dxf(
    msp,
    logo_bytes: bytes,
    clear_bounds: tuple[int, int],
    scale: int,
    border: int,
    logo_width_mm: Optional[float],
    logo_height_mm: Optional[float],
    dark_rgb: tuple[int, int, int],
    qr_size: int,
) -> None:
    """將 SVG logo 轉換為 DXF 圖形並添加到模型中"""
    start, end = clear_bounds
    if end <= start:
        return
    
    try:
        root = ET.fromstring(logo_bytes)
    except ET.ParseError:
        return
    
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
    # 注意：在 SVG 中，logo 的 y 屬性是在 SVG 座標系中從上往下的距離
    # 在 DXF 中，我們需要先計算正確的居中位置，然後在轉換每個點時應用 Y 軸反轉
    # x_offset 和 y_offset 會在後面根據實際寬高調整以保持寬高比和居中
    x_offset_base = offset_units
    y_offset_base = offset_units
    
    # 解析 CSS 樣式（處理 <style> 標籤）
    css_classes = {}
    # 嘗試多種方式找到 defs 和 style
    defs = root.find(".//{http://www.w3.org/2000/svg}defs")
    if defs is None:
        defs = root.find(".//defs")
    if defs is not None:
        style_elem = defs.find(".//{http://www.w3.org/2000/svg}style")
        if style_elem is None:
            style_elem = defs.find(".//style")
        if style_elem is None:
            # 也檢查根元素下是否有 style
            style_elem = root.find(".//{http://www.w3.org/2000/svg}style")
            if style_elem is None:
                style_elem = root.find(".//style")
        
        if style_elem is not None:
            style_text = style_elem.text or ""
            if not style_text and hasattr(style_elem, 'tail'):
                style_text = style_elem.tail or ""
            
            if style_text:
                import re
                # 解析 CSS 類，例如 .cls-1 { fill: #231815; }
                # 支持多行和單行格式
                class_matches = re.findall(r'\.([^{]+)\s*\{[^}]*fill\s*:\s*([^;}]+)', style_text, re.DOTALL)
                for class_name, fill_value in class_matches:
                    css_classes[class_name.strip()] = fill_value.strip()
                    # 調試輸出
                    import sys
                    print(f"Found CSS class: {class_name.strip()} -> {fill_value.strip()}", file=sys.stderr)
    
    # 解析 SVG 並提取路徑和圖形
    # 獲取 SVG 的視圖框尺寸
    svg_width = 100.0
    svg_height = 100.0
    
    width_attr = root.get("width", "")
    height_attr = root.get("height", "")
    
    if width_attr:
        try:
            svg_width = float(width_attr.replace("px", "").replace("mm", "").replace("pt", "").replace("cm", ""))
        except (ValueError, AttributeError):
            pass
    
    if height_attr:
        try:
            svg_height = float(height_attr.replace("px", "").replace("mm", "").replace("pt", "").replace("cm", ""))
        except (ValueError, AttributeError):
            pass
    
    # 處理 viewBox：viewBox="x y width height"
    # 元素的座標是相對於 viewBox 的原點 (x, y) 的
    viewbox_x = 0.0
    viewbox_y = 0.0
    viewbox = root.get("viewBox", "")
    if viewbox:
        parts = viewbox.split()
        if len(parts) >= 4:
            try:
                viewbox_x = float(parts[0])
                viewbox_y = float(parts[1])
                svg_width = float(parts[2])
                svg_height = float(parts[3])
            except (ValueError, IndexError):
                pass
    
    if svg_width <= 0 or svg_height <= 0:
        svg_width = 100.0
        svg_height = 100.0
    
    # 計算縮放比例，保持寬高比
    # 使用統一的 scale，避免拉伸變形
    # 這對應於 SVG 中的 preserveAspectRatio="xMidYMid meet"
    # SVG 中 preserveAspectRatio="xMidYMid meet" 的行為：
    # 1. 保持寬高比（meet）
    # 2. 在 x 和 y 方向居中（xMidYMid）
    # 3. 縮放以適應給定的 width 和 height
    scale_x_uniform = width_units / svg_width
    scale_y_uniform = height_units / svg_height
    # 使用較小的 scale 以確保 logo 完全適配，保持寬高比
    uniform_scale = min(scale_x_uniform, scale_y_uniform)
    scale_x = uniform_scale
    scale_y = uniform_scale
    
    # 重新計算實際的寬高（保持寬高比後的尺寸）
    actual_width = svg_width * uniform_scale
    actual_height = svg_height * uniform_scale
    
    # 調整 x_offset 和 y_offset 以居中（如果實際尺寸小於可用空間）
    # 在 SVG 中，preserveAspectRatio="xMidYMid meet" 會自動居中 logo
    # SVG 會計算縮放後的尺寸，然後在給定的區域內居中
    # 在 DXF 中，我們需要手動計算這個居中位置
    # 居中邏輯：如果實際尺寸小於可用空間，需要額外偏移以居中
    # 
    # 重要：在 SVG 中，logo 的 y 屬性是 offset_units + max(0.0, (clear_units - height_units) / 2)
    # 但在 SVG 中，preserveAspectRatio 會進一步居中，所以實際渲染位置會基於縮放後的尺寸
    #
    # SVG 實際渲染邏輯：
    # 1. logo_y = offset_units + max(0.0, (clear_units - height_units) / 2)
    # 2. preserveAspectRatio 會在 logo_y 到 logo_y + height_units 區域內居中 logo
    # 3. 如果 actual_height < height_units，那麼實際的 logo 頂部位置 = logo_y + (height_units - actual_height) / 2
    #
    # 在 DXF 中，我們直接計算最終的 logo 頂部位置：
    # y_offset = offset_units + max(0.0, (clear_units - height_units) / 2) + (height_units - actual_height) / 2
    # 
    # 先計算 SVG 中的基礎居中調整（對應 SVG 中 logo 的 y 屬性）
    svg_base_y_adjust = max(0.0, (clear_units - height_units) / 2)
    # 然後計算 preserveAspectRatio 的居中調整
    preserve_aspect_y_adjust = (height_units - actual_height) / 2
    
    x_offset_adjust = (width_units - actual_width) / 2
    y_offset_adjust = svg_base_y_adjust + preserve_aspect_y_adjust
    
    # 最終的偏移量（居中）
    # 在 SVG 中，logo 被設置為：
    #   x = offset_units + max(0.0, (clear_units - width_units) / 2)
    #   y = offset_units + max(0.0, (clear_units - height_units) / 2)
    #   width = width_units
    #   height = height_units
    #   preserveAspectRatio="xMidYMid meet"
    # 
    # preserveAspectRatio="xMidYMid meet" 的行為：
    # 1. 保持寬高比（meet）
    # 2. 在 x 和 y 方向居中（xMidYMid）
    # 3. 這意味著 logo 會在給定的 (x, y, width, height) 區域內居中
    #
    # 實際渲染邏輯：
    # 1. logo 會被縮放到 actual_width x actual_height（保持寬高比）
    # 2. logo 會在 (x, y) 到 (x+width, y+height) 區域內居中
    # 3. 所以實際的 logo 頂部位置 = y + (height - actual_height) / 2
    #
    # 在 DXF 中，我們需要確保 logo 的中心點與清除區域的中心點對齊
    # 清除區域的中心 = offset_units + clear_units / 2
    # Logo 的中心（在 SVG 座標系中）= y_offset + actual_height / 2
    # 所以：y_offset + actual_height / 2 = offset_units + clear_units / 2
    # 因此：y_offset = offset_units + clear_units / 2 - actual_height / 2
    # 簡化：y_offset = offset_units + (clear_units - actual_height) / 2
    
    # 使用中心對齊的方式計算 y_offset
    # 在 SVG 中，preserveAspectRatio="xMidYMid meet" 會在給定的區域內居中 logo
    # Logo 的中心應該對齊清除區域的中心
    clear_center_y = x_offset_base + clear_units / 2
    clear_center_x = x_offset_base + clear_units / 2
    
    # 計算 logo 內容的實際邊界框（遍歷所有元素找到最小/最大座標）
    # 這將幫助我們找到實際內容的中心點
    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')
    
    def find_bounds(elem, parent_transform=(1, 0, 0, 1, 0, 0)):
        nonlocal min_x, min_y, max_x, max_y
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        
        # 處理變換
        transform = elem.get("transform", "")
        tx, ty = 0, 0
        sx, sy = 1, 1
        if transform:
            import re
            if "translate" in transform:
                match = re.search(r'translate\(([^)]+)\)', transform)
                if match:
                    coords = match.group(1).split(",")
                    if len(coords) >= 2:
                        tx = float(coords[0].strip())
                        ty = float(coords[1].strip())
                    elif len(coords) == 1:
                        tx = float(coords[0].strip())
                        ty = tx
            if "scale" in transform:
                match = re.search(r'scale\(([^)]+)\)', transform)
                if match:
                    coords = match.group(1).split(",")
                    if len(coords) >= 2:
                        sx = float(coords[0].strip())
                        sy = float(coords[1].strip())
                    elif len(coords) == 1:
                        sx = float(coords[0].strip())
                        sy = sx
            parent_sx, _, _, parent_sy, parent_tx, parent_ty = parent_transform
            tx += parent_tx
            ty += parent_ty
            sx *= parent_sx
            sy *= parent_sy
        
        # 檢查 path、circle、rect、polygon 的座標
        if tag == "path":
            d = elem.get("d", "")
            if d:
                # 提取所有 M, L 命令的座標
                import re
                # 匹配 M, L, m, l 命令後面的座標
                matches = re.findall(r'[MLml]\s+([0-9.-]+)\s+([0-9.-]+)', d)
                for x_str, y_str in matches:
                    x = float(x_str) * sx + tx
                    y = float(y_str) * sy + ty
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)
                # 如果沒有找到座標，至少提取第一個 M 命令
                if not matches:
                    first_m = re.search(r'M\s+([0-9.-]+)\s+([0-9.-]+)', d)
                    if first_m:
                        x = float(first_m.group(1)) * sx + tx
                        y = float(first_m.group(2)) * sy + ty
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)
                        max_x = max(max_x, x)
                        max_y = max(max_y, y)
        elif tag == "circle":
            cx = float(elem.get("cx", 0)) * sx + tx
            cy = float(elem.get("cy", 0)) * sy + ty
            r = float(elem.get("r", 0)) * max(abs(sx), abs(sy))
            min_x = min(min_x, cx - r)
            min_y = min(min_y, cy - r)
            max_x = max(max_x, cx + r)
            max_y = max(max_y, cy + r)
        elif tag == "rect":
            x = float(elem.get("x", 0)) * sx + tx
            y = float(elem.get("y", 0)) * sy + ty
            w = float(elem.get("width", 0)) * abs(sx)
            h = float(elem.get("height", 0)) * abs(sy)
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x + w)
            max_y = max(max_y, y + h)
        elif tag == "polygon":
            points_str = elem.get("points", "")
            if points_str:
                import re
                points = re.findall(r'([0-9.-]+)\s*,?\s*([0-9.-]+)', points_str)
                for x_str, y_str in points:
                    x = float(x_str) * sx + tx
                    y = float(y_str) * sy + ty
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)
        
        # 遞歸處理子元素
        new_transform = (sx, 0, 0, sy, tx, ty)
        for child in elem:
            find_bounds(child, new_transform)
    
    # 遍歷所有元素找到邊界
    for child in root:
        find_bounds(child)
    
    # 如果找到了實際邊界，使用實際內容的中心；否則使用 viewBox 中心
    if min_x != float('inf') and min_y != float('inf'):
        logo_content_center_x = (min_x + max_x) / 2
        logo_content_center_y = (min_y + max_y) / 2
        import sys
        print(f"  Found actual content bounds: ({min_x}, {min_y}) to ({max_x}, {max_y})", file=sys.stderr)
        print(f"  Actual content center: ({logo_content_center_x}, {logo_content_center_y})", file=sys.stderr)
    else:
        # 如果沒有找到邊界，使用 viewBox 中心
        logo_content_center_x = viewbox_x + svg_width / 2
        logo_content_center_y = viewbox_y + svg_height / 2
        import sys
        print(f"  Using viewBox center: ({logo_content_center_x}, {logo_content_center_y})", file=sys.stderr)
    
    # 將 logo 內容中心映射到清除區域中心
    x_offset = clear_center_x - logo_content_center_x * uniform_scale
    y_offset = clear_center_y - logo_content_center_y * uniform_scale
    
    # 調試輸出
    import sys
    print(f"DXF Logo positioning (new method):", file=sys.stderr)
    print(f"  offset_units={x_offset_base}, clear_units={clear_units}", file=sys.stderr)
    print(f"  svg_width={svg_width}, svg_height={svg_height}, viewBox=({viewbox_x}, {viewbox_y}, {svg_width}, {svg_height})", file=sys.stderr)
    print(f"  actual_width={actual_width}, actual_height={actual_height}, uniform_scale={uniform_scale}", file=sys.stderr)
    print(f"  logo_content_center=({logo_content_center_x}, {logo_content_center_y})", file=sys.stderr)
    print(f"  clear_center=({clear_center_x}, {clear_center_y})", file=sys.stderr)
    print(f"  x_offset={x_offset}, y_offset={y_offset}", file=sys.stderr)
    print(f"  Expected logo content center in QR: ({logo_content_center_x * uniform_scale + x_offset}, {logo_content_center_y * uniform_scale + y_offset})", file=sys.stderr)
    
    # 重要：在 SVG 中，logo 的 y 屬性是 logo 頂部的位置（從上往下）
    # 但在 SVG 中，preserveAspectRatio="xMidYMid meet" 會在給定的區域內居中 logo
    # 這意味著如果 logo 保持寬高比後縮小了，它會在 height_units 區域內居中
    # 
    # 在 SVG 中：
    # - logo_y = offset_units + max(0.0, (clear_units - height_units) / 2)
    # - 如果 clear_units == height_units，那麼 logo_y = offset_units
    # - preserveAspectRatio 會在 logo_y 到 logo_y + height_units 區域內居中 logo
    # - 如果 actual_height < height_units，那麼實際的 logo 頂部位置 = logo_y + (height_units - actual_height) / 2
    #
    # 在 DXF 中，我們需要確保 y_offset 是 logo 頂部的位置（在 SVG 座標系中）
    # 注意：logo 內部元素的座標是相對於 logo 視圖框的原點的
    # 所以在轉換時，我們需要將 logo 內部元素的座標加上 y_offset
    
    # DXF Y 軸向上，SVG Y 軸向下，需要反轉
    total_qr_height = (qr_size + border * 2) * scale
    
    # 遞歸遍歷 SVG 元素，提取路徑和圖形
    def process_element(elem, parent_transform=(1, 0, 0, 1, 0, 0)):
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        
        # 檢查是否應該繪製（有填充或描邊）
        fill = elem.get("fill", None)
        
        # 檢查 class 屬性，從 CSS 類中獲取 fill
        class_attr = elem.get("class", "")
        if class_attr:
            # class 屬性可能包含多個類名，用空格分隔
            class_names = class_attr.split()
            for cls_name in class_names:
                if cls_name in css_classes:
                    fill = css_classes[cls_name]
                    # 調試輸出
                    import sys
                    print(f"Applied CSS class {cls_name} -> fill: {fill}", file=sys.stderr)
                    break
        
        # 檢查 style 屬性中的 fill
        style = elem.get("style", "")
        if style:
            import re
            fill_match = re.search(r'fill\s*:\s*([^;]+)', style)
            if fill_match:
                fill_style = fill_match.group(1).strip()
                if fill_style and fill_style not in ["none", "transparent"]:
                    fill = fill_style
        
        # 如果仍然沒有 fill，使用默認值
        if not fill or fill == "":
            fill = "black"  # SVG 默認填充為黑色
        
        if fill in ["none", "transparent", ""]:
            # 跳過無填充的元素
            fill = None
        
        # 處理變換
        transform = elem.get("transform", "")
        tx, ty = 0, 0
        sx, sy = 1, 1  # scale factors
        if transform:
            import re
            # 處理 translate 變換
            if "translate" in transform:
                match = re.search(r'translate\(([^)]+)\)', transform)
                if match:
                    coords = match.group(1).split(",")
                    if len(coords) >= 2:
                        tx = float(coords[0].strip())
                        ty = float(coords[1].strip())
                    elif len(coords) == 1:
                        tx = float(coords[0].strip())
                        ty = tx
            
            # 處理 scale 變換
            if "scale" in transform:
                match = re.search(r'scale\(([^)]+)\)', transform)
                if match:
                    coords = match.group(1).split(",")
                    if len(coords) >= 2:
                        sx = float(coords[0].strip())
                        sy = float(coords[1].strip())
                    elif len(coords) == 1:
                        sx = float(coords[0].strip())
                        sy = sx
            
            # 累積變換（考慮父元素的變換）
            # 簡化處理：只累積 translate
            parent_tx, parent_ty = parent_transform[4], parent_transform[5]
            tx += parent_tx
            ty += parent_ty
            sx *= parent_transform[0] if len(parent_transform) > 0 else 1
            sy *= parent_transform[3] if len(parent_transform) > 2 else 1
        
        # 處理 group (g) - 遞歸處理子元素
        if tag == "g":
            # 更新父變換矩陣
            new_transform = (
                sx, 0, 0, sy, tx, ty
            )
            for child in elem:
                process_element(child, new_transform)
            return
        
        # 處理路徑
        if tag == "path" and fill:
            d = elem.get("d", "")
            if d:
                try:
                    # 嘗試使用 svg.path 庫解析（如果可用）
                    try:
                        from svg.path import parse_path
                        path_obj = parse_path(d)
                        coords = []
                        
                        # 從 path 對象提取點
                        # 使用 point() 方法在路徑上採樣點
                        path_length = path_obj.length()
                        num_samples = max(50, min(500, int(path_length / 2)))  # 根據路徑長度決定採樣點數
                        if num_samples > 0:
                            for i in range(num_samples + 1):
                                t = i / num_samples if num_samples > 0 else 0
                                try:
                                    pos = path_obj.point(t)
                                    coords.append((pos.real, pos.imag))
                                except Exception:
                                    # 如果某個點無法計算，跳過
                                    pass
                        
                        if len(coords) > 1:
                            # 轉換坐標到 DXF 空間
                            dxf_coords = []
                            for x_svg, y_svg in coords:
                                # 應用 scale 變換
                                # 注意：SVG 元素的座標是相對於 viewBox 原點的
                                # 所以需要先減去 viewBox 原點
                                x_svg_relative = x_svg - viewbox_x
                                y_svg_relative = y_svg - viewbox_y
                                x_scaled = x_svg_relative * sx
                                y_scaled = y_svg_relative * sy
                                # SVG 坐標轉換到 DXF 空間（考慮 transform）
                                # 注意：在 SVG 中，preserveAspectRatio 會將 logo 縮放並居中
                                # 縮放後的 logo 中心應該對齊清除區域的中心
                                # 所以我們需要確保元素座標相對於 logo 中心的偏移是正確的
                                x = x_scaled * scale_x + x_offset + tx * scale_x
                                # SVG Y 軸向下，DXF Y 軸向上，需要反轉
                                # y_offset 是 logo 頂部的位置，但我們需要考慮 logo 元素相對於 logo 原點的偏移
                                y_svg_in_qr = y_scaled * scale_y + y_offset + ty * scale_y
                                y = total_qr_height - y_svg_in_qr
                                dxf_coords.append((x, y))
                            
                            # 調試輸出第一個點的位置
                            if len(dxf_coords) > 0:
                                import sys
                                first_x, first_y = dxf_coords[0]
                                first_x_svg, first_y_svg = coords[0]
                                # 重新計算以驗證
                                first_x_rel = first_x_svg - viewbox_x
                                first_y_rel = first_y_svg - viewbox_y
                                first_x_scaled = first_x_rel * sx
                                first_y_scaled = first_y_rel * sy
                                first_x_in_qr = first_x_scaled * scale_x + x_offset
                                first_y_svg_in_qr = first_y_scaled * scale_y + y_offset
                                expected_center_x = logo_content_center_x * uniform_scale + x_offset
                                expected_center_y = logo_content_center_y * uniform_scale + y_offset
                                print(f"  First path point SVG original: ({first_x_svg}, {first_y_svg})", file=sys.stderr)
                                print(f"  Relative to viewBox: ({first_x_rel}, {first_y_rel})", file=sys.stderr)
                                print(f"  Relative to logo center: ({first_x_svg - logo_content_center_x}, {first_y_svg - logo_content_center_y})", file=sys.stderr)
                                print(f"  First point in QR (SVG coords): ({first_x_in_qr}, {first_y_svg_in_qr})", file=sys.stderr)
                                print(f"  Expected logo center in QR: ({expected_center_x}, {expected_center_y})", file=sys.stderr)
                                print(f"  First point DXF: ({first_x}, {first_y}), total_qr_height={total_qr_height}", file=sys.stderr)
                            
                        if len(dxf_coords) > 1:
                            # 確保路徑閉合
                            if dxf_coords[-1] != dxf_coords[0]:
                                dxf_coords.append(dxf_coords[0])
                            # 使用 hatch 填充路徑（只有當 fill 不為 None 時）
                            if fill:
                                try:
                                    hatch = msp.add_hatch(color=ezdxf.colors.rgb2int(dark_rgb))
                                    hatch.paths.add_polyline_path(dxf_coords, flags=1)
                                    import sys
                                    print(f"Added path with {len(dxf_coords)} points", file=sys.stderr)
                                except Exception as hatch_exc:
                                    import sys
                                    print(f"Hatch creation error: {hatch_exc}", file=sys.stderr)
                    except ImportError:
                        # 如果 svg.path 不可用，使用簡單的正則表達式解析
                        import re
                        coords = []
                        current_x, current_y = 0, 0
                        
                        # 簡化解析：提取所有 M, L, H, V, C 命令的坐標
                        # 匹配 M, m, L, l, H, h, V, v, C, c, S, s, Q, q, T, t, A, a, Z, z 命令（絕對和相對）
                        # 注意：這裡只處理直線和簡單命令，曲線會被簡化為直線段
                        tokens = re.split(r'([MLHVCQSTAZmlhvcqstaz])', d)
                        
                        for i in range(1, len(tokens), 2):
                            if i + 1 >= len(tokens):
                                break
                            cmd = tokens[i]
                            params = tokens[i + 1] if i + 1 < len(tokens) else ""
                            
                            if cmd.upper() == "M":  # Move
                                nums = re.findall(r'([0-9.-]+)', params)
                                if len(nums) >= 2:
                                    if cmd == "M":
                                        current_x = float(nums[0])
                                        current_y = float(nums[1])
                                    else:  # m (相對)
                                        current_x += float(nums[0])
                                        current_y += float(nums[1])
                                    coords.append((current_x, current_y))
                            
                            elif cmd.upper() == "L":  # Line
                                nums = re.findall(r'([0-9.-]+)', params)
                                for j in range(0, len(nums), 2):
                                    if j + 1 < len(nums):
                                        if cmd == "L":
                                            current_x = float(nums[j])
                                            current_y = float(nums[j + 1])
                                        else:  # l (相對)
                                            current_x += float(nums[j])
                                            current_y += float(nums[j + 1])
                                        coords.append((current_x, current_y))
                            
                            elif cmd.upper() == "H":  # Horizontal line
                                nums = re.findall(r'([0-9.-]+)', params)
                                for num in nums:
                                    if cmd == "H":
                                        current_x = float(num)
                                    else:  # h (相對)
                                        current_x += float(num)
                                    coords.append((current_x, current_y))
                            
                            elif cmd.upper() == "V":  # Vertical line
                                nums = re.findall(r'([0-9.-]+)', params)
                                for num in nums:
                                    if cmd == "V":
                                        current_y = float(num)
                                    else:  # v (相對)
                                        current_y += float(num)
                                    coords.append((current_x, current_y))
                            
                            elif cmd.upper() == "Z":  # 閉合
                                if len(coords) > 0:
                                    coords.append(coords[0])
                        
                        if len(coords) > 1:
                            # 轉換坐標到 DXF 空間
                            dxf_coords = []
                            for x_svg, y_svg in coords:
                                # 注意：SVG 元素的座標是相對於 viewBox 原點的
                                x_svg_relative = x_svg - viewbox_x
                                y_svg_relative = y_svg - viewbox_y
                                x_scaled = x_svg_relative * sx
                                y_scaled = y_svg_relative * sy
                                x = x_scaled * scale_x + x_offset + tx * scale_x
                                y_svg_in_qr = y_scaled * scale_y + y_offset + ty * scale_y
                                y = total_qr_height - y_svg_in_qr
                                dxf_coords.append((x, y))
                            
                            if len(dxf_coords) > 1:
                                if dxf_coords[-1] != dxf_coords[0]:
                                    dxf_coords.append(dxf_coords[0])
                                hatch = msp.add_hatch(color=ezdxf.colors.rgb2int(dark_rgb))
                                hatch.paths.add_polyline_path(dxf_coords, flags=1)
                except Exception as e:  # noqa: BLE001
                    # 記錄錯誤但不中斷
                    import sys
                    print(f"Path parsing error: {e}", file=sys.stderr)
                    pass
        
        # 處理圓形
        elif tag == "circle" and fill:
            cx_svg = float(elem.get("cx", 0))
            cy_svg = float(elem.get("cy", 0))
            # 注意：SVG 元素的座標是相對於 viewBox 原點的
            cx_svg_relative = cx_svg - viewbox_x
            cy_svg_relative = cy_svg - viewbox_y
            # 應用 scale 變換
            cx_scaled = cx_svg_relative * sx
            cy_scaled = cy_svg_relative * sy
            cx = cx_scaled * scale_x + x_offset + tx * scale_x
            cy_temp = cy_scaled * scale_y + y_offset + ty * scale_y
            # 反轉 Y 軸
            cy = total_qr_height - cy_temp
            r = float(elem.get("r", 0)) * min(scale_x * sx, scale_y * sy)
            if r > 0:
                # 生成圓形點
                segments = 80
                circle_pts = [
                    (
                        cx + r * math.cos(2 * math.pi * i / segments),
                        cy + r * math.sin(2 * math.pi * i / segments),
                    )
                    for i in range(segments)
                ]
                path = [(p[0], p[1]) for p in circle_pts]
                path.append(path[0])
                hatch = msp.add_hatch(color=ezdxf.colors.rgb2int(dark_rgb))
                hatch.paths.add_polyline_path(path, flags=1)
        
        # 處理矩形
        elif tag == "rect" and fill:
            x_svg = float(elem.get("x", 0))
            y_svg = float(elem.get("y", 0))
            w_svg = float(elem.get("width", 0))
            h_svg = float(elem.get("height", 0))
            # 注意：SVG 元素的座標是相對於 viewBox 原點的
            x_svg_relative = x_svg - viewbox_x
            y_svg_relative = y_svg - viewbox_y
            # 應用 scale 變換
            x_scaled = x_svg_relative * sx
            y_scaled = y_svg_relative * sy
            w_scaled = w_svg * sx
            h_scaled = h_svg * sy
            x = x_scaled * scale_x + x_offset + tx * scale_x
            w = w_scaled * scale_x
            h = h_scaled * scale_y
            # 反轉 Y 軸（矩形需要從底部開始）
            y_svg_abs = y_scaled * scale_y + y_offset + ty * scale_y
            y = total_qr_height - (y_svg_abs + h)
            if w > 0 and h > 0:
                rect_path = [
                    (x, y),
                    (x + w, y),
                    (x + w, y + h),
                    (x, y + h),
                    (x, y)
                ]
                hatch = msp.add_hatch(color=ezdxf.colors.rgb2int(dark_rgb))
                hatch.paths.add_polyline_path(rect_path, flags=1)
        
        # 處理多邊形
        elif tag == "polygon" and fill:
            points_str = elem.get("points", "")
            if points_str:
                try:
                    import re
                    coords = []
                    points = re.findall(r'([0-9.-]+)\s*,?\s*([0-9.-]+)', points_str)
                    for x_str, y_str in points:
                        # 注意：SVG 元素的座標是相對於 viewBox 原點的
                        x_svg_relative = float(x_str) - viewbox_x
                        y_svg_relative = float(y_str) - viewbox_y
                        # 應用 scale 變換
                        x_scaled = x_svg_relative * sx
                        y_scaled = y_svg_relative * sy
                        x = x_scaled * scale_x + x_offset + tx * scale_x
                        y_svg_in_qr = y_scaled * scale_y + y_offset + ty * scale_y
                        y = total_qr_height - y_svg_in_qr
                        coords.append((x, y))
                    
                    if len(coords) > 1:
                        coords.append(coords[0])  # 閉合
                        hatch = msp.add_hatch(color=ezdxf.colors.rgb2int(dark_rgb))
                        hatch.paths.add_polyline_path(coords, flags=1)
                except Exception:  # noqa: BLE001
                    pass
        
        # 遞歸處理子元素（如果元素沒有被跳過）
        if fill is not None:  # 只有當元素有填充時才處理子元素
            for child in elem:
                # 更新父變換矩陣
                new_transform = (
                    sx, 0, 0, sy, tx, ty
                )
                process_element(child, new_transform)
        else:
            # 即使沒有填充，也要遞歸處理子元素（可能子元素有填充）
            for child in elem:
                new_transform = (
                    sx, 0, 0, sy, tx, ty
                )
                process_element(child, new_transform)
    
    # 處理 SVG 根元素及其子元素
    # 初始變換矩陣：(scale_x, 0, 0, scale_y, translate_x, translate_y)
    initial_transform = (1, 0, 0, 1, 0, 0)
    for child in root:
        process_element(child, initial_transform)


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
            logo_width_mm_dxf = _safe_float(payload.get("qrWidthMm"), DEFAULT_QR_MM)
            logo_height_mm_dxf = _safe_float(payload.get("qrHeightMm"), logo_width_mm_dxf)
            result_bytes = _generate_dxf(
                matrix,
                scale,
                border,
                dark,
                light,
                logo_bytes=logo_bytes,
                clear_bounds=clear_bounds,
                logo_width_mm=logo_width_mm_dxf,
                logo_height_mm=logo_height_mm_dxf,
            )
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
