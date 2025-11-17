#!/usr/bin/env python3
"""離線 QR 碼產生工具

此指令列工具利用 segno 套件在本機產生 QR Code，可輸出 PNG / SVG / EPS / PDF。
PNG 格式可選擇疊加自訂 Logo（支援 PNG / JPG / SVG）。
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import Optional

try:
    import segno
except ImportError as exc:  # pragma: no cover
    print("[錯誤] 缺少 segno 套件，請先執行: pip install segno pillow", file=sys.stderr)
    raise

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


SUPPORTED_FORMATS = {"png", "svg", "eps", "pdf"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="離線 QR 碼產生工具")
    parser.add_argument("data", help="要編碼的內容，例如網址或文字")
    parser.add_argument("output", help="輸出檔案路徑 (副檔名決定格式，例如 output.png)")
    parser.add_argument(
        "--scale",
        type=int,
        default=8,
        help="單一模組像素大小 (預設: 8)，數值越大整體圖片越大",
    )
    parser.add_argument(
        "--border",
        type=int,
        default=4,
        help="邊框模組寬度 (預設: 4)",
    )
    parser.add_argument(
        "--dark",
        default="#000000",
        help="深色模組的顏色 (預設: #000000)",
    )
    parser.add_argument(
        "--light",
        default="#ffffff",
        help="淺色背景的顏色 (預設: #ffffff)",
    )
    parser.add_argument(
        "--logo",
        help="僅 PNG 可用：欲疊加的 Logo 圖片路徑 (支援 PNG / JPG / SVG)",
    )
    parser.add_argument(
        "--logo-scale",
        type=float,
        default=0.22,
        help="Logo 寬度占 QR 碼寬度的比例 (預設: 0.22)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="關閉產生過程中的訊息輸出",
    )
    return parser.parse_args()


def ensure_deps_for_logo():
    if Image is None:
        raise RuntimeError("缺少 Pillow，請執行 pip install pillow 以支援 Logo 疊加。")


def add_logo_to_png(png_bytes: bytes, logo_path: Path, logo_scale: float) -> bytes:
    """在 PNG 中加入 Logo，回傳帶 Logo 的 PNG bytes。"""
    ensure_deps_for_logo()

    base = Image.open(io.BytesIO(png_bytes)).convert("RGBA")

    # 讀取 Logo，若為 SVG 需轉為 PNG
    logo_data = logo_path.read_bytes()
    if logo_path.suffix.lower() == ".svg":
        try:
            import cairosvg  # type: ignore
        except ImportError as exc:
            raise RuntimeError("加入 SVG Logo 需要 cairosvg，請先安裝: pip install cairosvg") from exc
        logo_png = cairosvg.svg2png(bytestring=logo_data)
        logo = Image.open(io.BytesIO(logo_png)).convert("RGBA")
    else:
        logo = Image.open(io.BytesIO(logo_data)).convert("RGBA")

    # 依比例縮放 Logo
    logo_scale = max(0.05, min(logo_scale, 0.5))
    target_width = int(base.width * logo_scale)
    target_height = int(logo.height * (target_width / logo.width))
    logo = logo.resize((target_width, target_height), Image.LANCZOS)

    # 將 Logo 置中
    pos = ((base.width - logo.width) // 2, (base.height - logo.height) // 2)
    base.alpha_composite(logo, dest=pos)

    output = io.BytesIO()
    base.save(output, format="PNG")
    return output.getvalue()


def generate_qr(
    data: str,
    output_path: Path,
    scale: int,
    border: int,
    dark: str,
    light: str,
    logo: Optional[Path],
    logo_scale: float,
    quiet: bool,
) -> None:
    fmt = output_path.suffix.lower().lstrip('.')
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"不支援的輸出格式: {fmt}，請使用 {', '.join(sorted(SUPPORTED_FORMATS))}")

    qr = segno.make(data, error="h")  # 高容錯等級，方便放置 Logo

    if fmt == "png":
        buffer = io.BytesIO()
        qr.save(
            buffer,
            kind="png",
            scale=scale,
            border=border,
            dark=dark,
            light=light,
        )
        png_bytes = buffer.getvalue()

        if logo:
            png_bytes = add_logo_to_png(png_bytes, logo, logo_scale)
        output_path.write_bytes(png_bytes)
    else:
        qr.save(
            output_path,
            kind=fmt,
            scale=scale,
            border=border,
            dark=dark,
            light=light,
        )

    if not quiet:
        print(f"已產生 {output_path} ({fmt.upper()})")


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)

    logo_path = Path(args.logo).expanduser().resolve() if args.logo else None
    if logo_path and not logo_path.exists():
        raise FileNotFoundError(f"無法找到 Logo 檔案: {logo_path}")

    generate_qr(
        data=args.data,
        output_path=output_path,
        scale=args.scale,
        border=args.border,
        dark=args.dark,
        light=args.light,
        logo=logo_path,
        logo_scale=args.logo_scale,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover
        print(f"[錯誤] {exc}", file=sys.stderr)
        sys.exit(1)
