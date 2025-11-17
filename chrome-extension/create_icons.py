#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
創建簡單的 QR 碼圖標
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    import os

    def create_icon(size, filename):
        """創建圖標"""
        # 創建圖片
        img = Image.new('RGB', (size, size), color='#4CAF50')
        draw = ImageDraw.Draw(img)
        
        # 繪製 QR 碼樣式的圖案（簡化版）
        # 繪製三個角（模擬 QR 碼的定位點）
        corner_size = size // 4
        margin = size // 8
        
        # 左上角
        draw.rectangle([margin, margin, margin + corner_size, margin + corner_size], 
                      fill='white', outline='white')
        draw.rectangle([margin + corner_size//4, margin + corner_size//4, 
                       margin + 3*corner_size//4, margin + 3*corner_size//4], 
                      fill='#4CAF50')
        
        # 右上角
        draw.rectangle([size - margin - corner_size, margin, 
                       size - margin, margin + corner_size], 
                      fill='white', outline='white')
        draw.rectangle([size - margin - 3*corner_size//4, margin + corner_size//4, 
                       size - margin - corner_size//4, margin + 3*corner_size//4], 
                      fill='#4CAF50')
        
        # 左下角
        draw.rectangle([margin, size - margin - corner_size, 
                       margin + corner_size, size - margin], 
                      fill='white', outline='white')
        draw.rectangle([margin + corner_size//4, size - margin - 3*corner_size//4, 
                       margin + 3*corner_size//4, size - margin - corner_size//4], 
                      fill='#4CAF50')
        
        # 保存圖片
        img.save(filename)
        print(f"創建圖標: {filename} ({size}x{size})")

    # 創建圖標目錄
    icons_dir = 'icons'
    os.makedirs(icons_dir, exist_ok=True)
    
    # 創建不同尺寸的圖標
    create_icon(16, os.path.join(icons_dir, 'icon16.png'))
    create_icon(48, os.path.join(icons_dir, 'icon48.png'))
    create_icon(128, os.path.join(icons_dir, 'icon128.png'))
    
    print("所有圖標創建完成！")

except ImportError:
    print("需要 Pillow 套件來創建圖標")
    print("請執行: pip install Pillow")
    print("\n或者您可以手動創建圖標檔案：")
    print("1. 使用線上工具: https://www.favicon-generator.org/")
    print("2. 或使用其他圖片編輯工具")
    print("3. 將圖標放在 icons/ 目錄下")

except Exception as e:
    print(f"創建圖標時發生錯誤: {e}")
    print("\n您可以手動創建圖標檔案或使用線上工具")

