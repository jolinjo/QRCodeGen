#!/usr/bin/env python3
"""Gradio 版 QR Code 產生器"""
from __future__ import annotations

import io
from typing import Tuple

import gradio as gr
import segno
from PIL import Image


def generate_qr(data: str, scale: int, border: int, dark: str, light: str, logo_file) -> Tuple[str, bytes]:
    if not data.strip():
        raise gr.Error("請輸入要編碼的文字或網址")

    qr = segno.make(data.strip(), error="h")
    buffer = io.BytesIO()
    qr.save(buffer, kind="png", scale=scale, border=border, dark=dark, light=light)
    png_bytes = buffer.getvalue()

    if logo_file is not None:
        img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        logo = Image.open(logo_file.name).convert("RGBA")
        logo_w = int(img.width * 0.22)
        logo_h = int(logo.height * (logo_w / logo.width))
        logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
        pos = ((img.width - logo.width) // 2, (img.height - logo.height) // 2)
        img.alpha_composite(logo, dest=pos)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()

    return "產生成功！", png_bytes


with gr.Blocks(title="QR Code Generator") as demo:
    gr.Markdown("# 🔳 離線 QR Code 產生器 (Gradio)")
    gr.Markdown("使用 segno 直接在本地產生 QR Code，可選擇上傳 Logo。")

    with gr.Row():
        data_input = gr.Textbox(label="內容", placeholder="https://example.com", lines=2)
        logo_input = gr.File(label="Logo (可選，PNG/JPG)")

    with gr.Row():
        scale_input = gr.Slider(1, 20, value=8, label="模組大小 (scale)")
        border_input = gr.Slider(0, 10, value=4, label="邊框寬度 (border)")
    with gr.Row():
        dark_input = gr.ColorPicker(value="#000000", label="深色模組")
        light_input = gr.ColorPicker(value="#ffffff", label="淺色背景")

    generate_btn = gr.Button("產生 QR Code")
    status = gr.Markdown()
    output_image = gr.Image(type="png", label="預覽")

    generate_btn.click(
        fn=generate_qr,
        inputs=[data_input, scale_input, border_input, dark_input, light_input, logo_input],
        outputs=[status, output_image],
    )

if __name__ == "__main__":
    demo.launch()
