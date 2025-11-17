#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試 GUI 啟動
"""

import os
import sys

# 設置環境變數來抑制警告
os.environ['TK_SILENCE_DEPRECATION'] = '1'

# 嘗試導入並創建 GUI
try:
    import tkinter as tk
    from tkinter import ttk
    
    print("正在創建 GUI 視窗...")
    
    # 創建主視窗
    root = tk.Tk()
    root.title("QR 碼產生器測試")
    root.geometry("400x300")
    
    # 添加標籤
    label = ttk.Label(root, text="GUI 測試成功！", font=("Arial", 16))
    label.pack(pady=50)
    
    # 添加關閉按鈕
    def close_window():
        root.destroy()
        print("視窗已關閉")
    
    button = ttk.Button(root, text="關閉", command=close_window)
    button.pack(pady=20)
    
    print("GUI 視窗已創建，應該可以看到視窗了")
    print("如果看不到視窗，請檢查是否有其他錯誤")
    
    # 運行主循環
    root.mainloop()
    
except Exception as e:
    print(f"錯誤: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

