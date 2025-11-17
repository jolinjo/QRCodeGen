#!/usr/bin/env python3
"""Streamlit 版 QR Code 產生器"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

import segno
import streamlit as st
from PIL import Image

SUPPORTED_FORMATS = ["png", "svg", "eps", "pdf"]

st.set_page_config(page_title="QR Code Generator", page_icon="🔳")
st.title("🔳 離線 QR Code 產生器")
st.markdown("使用 [segno](https://pypi.org/project/segno/) 在本地產生 QR Code，無需任何 API。")

with st.sidebar:
    st.header("輸出設定")
    scale = st.slider("模組大小 (scale)", 1, 20, 8)
    border = st.slider("邊框寬度 (border)", 0, 10, 4)
    dark = st.color_picker("深色模組", "#000000")
    light = st.color_picker("淺色背景", "#ffffff")
    fmt = st.selectbox("輸出格式", SUPPORTED_FORMATS, index=0)
    logo_file = st.file_uploader("Logo (僅 PNG 支援疊加)", type=["png", "jpg", "jpeg"])
    logo_scale = st.slider("Logo 與 QR 寬度比例", 0.05, 0.5, 0.22)

content = st.text_area("輸入內容 (網址或文字)", "https://example.com")
col_preview, col_download = st.columns([2, 1])

if st.button("產生 QR Code", type="primary"):
    if not content.strip():
        st.error("請輸入要編碼的文字或網址")
    else:
        qr = segno.make(content.strip(), error="h")
        st.success("產生成功！")

        if fmt == "png":
            buffer = io.BytesIO()
            qr.save(buffer, kind="png", scale=scale, border=border, dark=dark, light=light)
            png_bytes = buffer.getvalue()

            if logo_file:
                img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
                logo = Image.open(logo_file).convert("RGBA")
                target_w = int(img.width * logo_scale)
                target_h = int(logo.height * (target_w / logo.width))
                logo = logo.resize((target_w, target_h), Image.LANCZOS)
                pos = ((img.width - logo.width) // 2, (img.height - logo.height) // 2)
                img.alpha_composite(logo, dest=pos)
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                png_bytes = buffer.getvalue()

            with col_preview:
                st.image(png_bytes, caption="預覽 (PNG)")
            with col_download:
                st.download_button(
                    label="下載 QR Code",
                    data=png_bytes,
                    file_name="qrcode.png",
                    mime="image/png",
                )
        else:
            outfile = Path(f"qrcode.{fmt}")
            qr.save(outfile, kind=fmt, scale=scale, border=border, dark=dark, light=light)
            with outfile.open("rb") as f:
                data = f.read()
            with col_preview:
                st.info(f"已產生 {outfile.name}")
            with col_download:
                st.download_button(
                    label=f"下載 QR Code ({fmt.upper()})",
                    data=data,
                    file_name=outfile.name,
                )
            outfile.unlink(missing_ok=True)
else:
    st.info("輸入內容後點擊「產生 QR Code」。")
