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
        for x, y in pts[1:]:
            path_cmds.append(f"L {x} {y}")
        path_cmds.append("Z")
        return " ".join(path_cmds)

    def add_finder(svg_root, center_row: int, center_col: int) -> None:
        cx = (center_col + border + 0.5) * scale
        cy = (center_row + border + 0.5) * scale
        outer = circle_points(cx, cy, scale * 3.5)
        inner_ring = circle_points(cx, cy, scale * 2.5)
        inner = circle_points(cx, cy, scale * 1.5)

        path_data = circle_path(outer) + " " + circle_path(inner_ring, reverse=True)
        ET.SubElement(
            svg_root,
            "path",
            attrib={
                "fill": dark,
                "d": path_data,
            },
        )

        ET.SubElement(
            svg_root,
            "path",
            attrib={
                "fill": dark,
                "d": circle_path(inner),
            },
        )

    size = len(matrix)
    total = size + border * 2
    width = height = total * scale

    svg = ET.Element(
        "svg",
        attrib={
            "xmlns": "http://www.w3.org/2000/svg",
            "width": str(width),
            "height": str(height),
            "viewBox": f"0 0 {width} {height}",
        },
    )

    for row_idx, row in enumerate(matrix):
        for col_idx, cell in enumerate(row):
            if not cell:
                continue
            if in_finder(row_idx, col_idx, size):
                continue
            cx = (col_idx + border + 0.5) * scale
            cy = (row_idx + border + 0.5) * scale
            half = scale / 2
            points = (
                f"{cx},{cy - half} "
                f"{cx + half},{cy} "
                f"{cx},{cy + half} "
                f"{cx - half},{cy}"
            )
            ET.SubElement(
                svg,
                "polygon",
                attrib={
                    "points": points,
                    "fill": dark,
                },
            )

    # Add circular finder patterns
    add_finder(svg, 3, 3)
    add_finder(svg, 3, size - 4)
    add_finder(svg, size - 4, 3)

    return ET.tostring(svg, encoding="unicode")


def _parse_length(value: Optional[str], fallback: float) -> float:
    if value is None:
        return fallback
    value = value.strip()
    if not value:
        return fallback
    for suffix in ("px", "pt", "cm", "mm", "in", "pc", "%"):
        if value.endswith(suffix):
            value = value[: -len(suffix)]
            break
    try:
        return float(value)
    except ValueError:
        return fallback


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

    if logo_root.tag.endswith("svg"):
        width_attr = _parse_length(logo_root.get("width"), width_units)
        height_attr = _parse_length(logo_root.get("height"), height_units or width_units)
        if width_attr <= 0 or height_attr <= 0:
            width_attr = width_units
            height_attr = height_units
        if not logo_root.get("viewBox"):
            logo_root.set("viewBox", f"0 0 {width_attr} {height_attr}")
        logo_root.set("preserveAspectRatio", "xMidYMid meet")
        logo_root.set("width", str(width_units))
        logo_root.set("height", str(height_units))
        logo_root.set("x", str(x_offset))
        logo_root.set("y", str(y_offset))
        root.append(logo_root)
    else:
        # Wrap non-<svg> root elements
        namespace = root.tag.split("}")[0][1:] if root.tag.startswith("{") else ""
        tag = f"{{{namespace}}}svg" if namespace else "svg"
        wrapper = ET.Element(tag, {
            "width": str(width_units),
            "height": str(height_units),
            "x": str(x_offset),
            "y": str(y_offset),
            "viewBox": "0 0 100 100",
            "preserveAspectRatio": "xMidYMid meet",
        })
        wrapper.append(logo_root)
        root.append(wrapper)

    return ET.tostring(root, encoding="unicode")


def _generate_ai(svg_text: str) -> bytes:
    eps_bytes = cairosvg.svg2ps(bytestring=svg_text.encode("utf-8"))
    header = [
        "%!PS-Adobe-3.0",
        "%AI8_SaveAs: 1",
        "%AI8_FileFormat 4",
        "%AI8_ColorModel: 1",
        "%%Creator: QR Generator",
        "%%EndComments",
    ]
    eps_lines = eps_bytes.splitlines()
    if eps_lines and eps_lines[0].startswith(b"%!PS-Adobe"):
        eps_lines = eps_lines[1:]
    combined = "\n".join(header).encode("utf-8") + b"\n" + b"\n".join(eps_lines) + b"\n"
    return combined


def _generate_dxf(
    matrix,
    scale: int,
    border: int,
    dark: str,
    light: str,
) -> bytes:
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    dark_rgb = _hex_to_rgb(dark)
    dark_color = colors.rgb2int(dark_rgb)

    size = len(matrix)

    def in_finder(row: int, col: int) -> bool:
        tl = row < 7 and col < 7
        tr = row < 7 and col >= size - 7
        bl = row >= size - 7 and col < 7
        return tl or tr or bl

    def add_diamond(cx: float, cy: float) -> None:
        half = scale / 2
        points = [
            (cx, cy - half),
            (cx + half, cy),
            (cx, cy + half),
            (cx - half, cy),
        ]
        hatch = msp.add_hatch(color=0)
        hatch.dxf.true_color = dark_color
        hatch.paths.add_polyline_path(points, is_closed=True)

    def add_circle(center_row: int, center_col: int) -> None:
        cx = (center_col + border + 0.5) * scale
        cy = (center_row + border + 0.5) * scale

        def ring(radius_outer: float, radius_inner: float | None, color_int: int) -> None:
            segments = 96
            outer = [
                (
                    cx + radius_outer * math.cos(2 * math.pi * i / segments),
                    cy + radius_outer * math.sin(2 * math.pi * i / segments),
                )
                for i in range(segments)
            ]
            hatch = msp.add_hatch(color=0)
            hatch.dxf.true_color = color_int
            hatch.paths.add_polyline_path(outer, is_closed=True)
            if radius_inner:
                inner = [
                    (
                        cx + radius_inner * math.cos(2 * math.pi * i / segments),
                        cy + radius_inner * math.sin(2 * math.pi * i / segments),
                    )
                    for i in range(segments, -1, -1)
                ]
                hatch.paths.add_polyline_path(inner, is_closed=True, flags=1)

        ring(scale * 3.5, scale * 2.5, dark_color)

        def filled_circle(radius: float, color_int: int) -> None:
            segments = 96
            pts = [
                (
                    cx + radius * math.cos(2 * math.pi * i / segments),
                    cy + radius * math.sin(2 * math.pi * i / segments),
                )
                for i in range(segments)
            ]
            hatch = msp.add_hatch(color=0)
            hatch.dxf.true_color = color_int
            hatch.paths.add_polyline_path(pts, is_closed=True)

        filled_circle(scale * 1.5, dark_color)

    for row_idx, row in enumerate(matrix):
        for col_idx, cell in enumerate(row):
            if not cell or in_finder(row_idx, col_idx):
                continue

            cx = (col_idx + border + 0.5) * scale
            cy = (row_idx + border + 0.5) * scale
            add_diamond(cx, cy)

    add_circle(3, 3)
    add_circle(3, size - 4)
    add_circle(size - 4, 3)

    text_buffer = io.StringIO()
    doc.write(text_buffer)
    return text_buffer.getvalue().encode("utf-8")


@app.after_request
def add_cors_headers(response: Response) -> Response:
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response


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

    metadata = {
        "version": int(getattr(qr, "version", 0) or 0),
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
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5002, help="Port to bind (default 5002)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
