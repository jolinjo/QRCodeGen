#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QR 碼產生器 GUI 介面
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import io
import sys
import os

# 添加當前目錄到路徑以導入 qr_api
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from qr_api import QRCodeMonkeyAPI


class QRCodeGeneratorGUI:
    """QR 碼產生器 GUI 類別"""
    
    def __init__(self, root):
        """初始化 GUI"""
        self.root = root
        self.root.title("QR 碼產生器")
        self.root.geometry("1000x800")
        
        # API 客戶端
        self.api = QRCodeMonkeyAPI()
        
        # 變數
        self.qr_image = None
        self.current_qr_data = None
        
        # 建立 UI
        self.create_widgets()
        
        # 選項值（根據 API 文檔）
        self.body_types = ["square", "circle", "rounded-pointed", "extra-rounded", "pointed", "pointed-smooth", "pointed-edge", "square-smooth", "dots", "classy", "classy-rounded", "rounded", "smooth", "smooth-rounded-edge", "rounded-edge", "smooth-edge"]
        # 簡化 eye 和 eyeBall 選項，顯示常用的
        self.eye_types = [f"frame{i}" for i in range(20)]
        self.eyeBall_types = [f"ball{i}" for i in range(20)]
    
    def create_widgets(self):
        """建立 UI 元件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # 左側：輸入和設定區域
        left_frame = ttk.LabelFrame(main_frame, text="設定", padding="10")
        left_frame.pack(side="left", fill="both", expand=False, padx=(0, 10))
        
        # 右側：預覽區域
        right_frame = ttk.LabelFrame(main_frame, text="預覽", padding="10")
        right_frame.pack(side="right", fill="both", expand=True)
        
        # 建立左側內容
        self.create_input_section(left_frame)
        self.create_config_section(left_frame)
        
        # 建立右側內容
        self.create_preview_section(right_frame)
    
    def create_input_section(self, parent):
        """建立輸入區域"""
        input_frame = ttk.LabelFrame(parent, text="QR 碼內容", padding="10")
        input_frame.pack(fill="x", pady=(0, 10))
        
        # URL 輸入
        ttk.Label(input_frame, text="網址/文字:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_var = tk.StringVar(value="https://www.qrcode-monkey.com")
        url_entry = ttk.Entry(input_frame, textvariable=self.url_var, width=40)
        url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        input_frame.columnconfigure(1, weight=1)
        
        # 大小設定
        ttk.Label(input_frame, text="大小:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.size_var = tk.IntVar(value=300)
        size_spinbox = ttk.Spinbox(input_frame, from_=100, to=1000, textvariable=self.size_var, width=10)
        size_spinbox.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        # 格式選擇
        ttk.Label(input_frame, text="格式:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.format_var = tk.StringVar(value="png")
        format_combo = ttk.Combobox(input_frame, textvariable=self.format_var, values=["png", "svg", "pdf", "eps"], state="readonly", width=10)
        format_combo.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        
        # 產生按鈕
        generate_btn = ttk.Button(input_frame, text="產生 QR 碼", command=self.generate_qr_code)
        generate_btn.grid(row=3, column=0, columnspan=2, pady=10)
    
    def create_config_section(self, parent):
        """建立客製化設定區域"""
        config_frame = ttk.LabelFrame(parent, text="客製化選項", padding="10")
        config_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Body 類型
        ttk.Label(config_frame, text="Body 類型:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.body_var = tk.StringVar(value="square")
        body_combo = ttk.Combobox(config_frame, textvariable=self.body_var, values=self.body_types, state="readonly", width=20)
        body_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        config_frame.columnconfigure(1, weight=1)
        
        # Eye 類型
        ttk.Label(config_frame, text="Eye 類型:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.eye_var = tk.StringVar(value="frame0")
        eye_combo = ttk.Combobox(config_frame, textvariable=self.eye_var, values=self.eye_types, state="readonly", width=20)
        eye_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # EyeBall 類型
        ttk.Label(config_frame, text="EyeBall 類型:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.eyeBall_var = tk.StringVar(value="ball0")
        eyeBall_combo = ttk.Combobox(config_frame, textvariable=self.eyeBall_var, values=self.eyeBall_types, state="readonly", width=20)
        eyeBall_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # 顏色設定區域
        color_frame = ttk.LabelFrame(config_frame, text="顏色設定", padding="5")
        color_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        color_frame.columnconfigure(1, weight=1)
        
        # Body 顏色
        ttk.Label(color_frame, text="Body 顏色:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.bodyColor_var = tk.StringVar(value="#000000")
        bodyColor_entry = ttk.Entry(color_frame, textvariable=self.bodyColor_var, width=10)
        bodyColor_entry.grid(row=0, column=1, sticky=tk.W, pady=3, padx=5)
        
        # 背景顏色
        ttk.Label(color_frame, text="背景顏色:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.bgColor_var = tk.StringVar(value="#ffffff")
        bgColor_entry = ttk.Entry(color_frame, textvariable=self.bgColor_var, width=10)
        bgColor_entry.grid(row=1, column=1, sticky=tk.W, pady=3, padx=5)
        
        # Eye 顏色
        ttk.Label(color_frame, text="Eye 顏色:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.eye1Color_var = tk.StringVar(value="#000000")
        eye1Color_entry = ttk.Entry(color_frame, textvariable=self.eye1Color_var, width=10)
        eye1Color_entry.grid(row=2, column=1, sticky=tk.W, pady=3, padx=5)
        
        # EyeBall 顏色
        ttk.Label(color_frame, text="EyeBall 顏色:").grid(row=3, column=0, sticky=tk.W, pady=3)
        self.eyeBall1Color_var = tk.StringVar(value="#000000")
        eyeBall1Color_entry = ttk.Entry(color_frame, textvariable=self.eyeBall1Color_var, width=10)
        eyeBall1Color_entry.grid(row=3, column=1, sticky=tk.W, pady=3, padx=5)
        
        # 漸層設定區域
        gradient_frame = ttk.LabelFrame(config_frame, text="漸層設定", padding="5")
        gradient_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        gradient_frame.columnconfigure(1, weight=1)
        
        # 漸層顏色1
        ttk.Label(gradient_frame, text="漸層顏色1:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.gradientColor1_var = tk.StringVar(value="")
        gradientColor1_entry = ttk.Entry(gradient_frame, textvariable=self.gradientColor1_var, width=10)
        gradientColor1_entry.grid(row=0, column=1, sticky=tk.W, pady=3, padx=5)
        
        # 漸層顏色2
        ttk.Label(gradient_frame, text="漸層顏色2:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.gradientColor2_var = tk.StringVar(value="")
        gradientColor2_entry = ttk.Entry(gradient_frame, textvariable=self.gradientColor2_var, width=10)
        gradientColor2_entry.grid(row=1, column=1, sticky=tk.W, pady=3, padx=5)
        
        # 漸層類型
        ttk.Label(gradient_frame, text="漸層類型:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self.gradientType_var = tk.StringVar(value="linear")
        gradientType_combo = ttk.Combobox(gradient_frame, textvariable=self.gradientType_var, values=["linear", "radial"], state="readonly", width=10)
        gradientType_combo.grid(row=2, column=1, sticky=tk.W, pady=3, padx=5)
        
        # Logo 設定
        logo_frame = ttk.LabelFrame(config_frame, text="Logo 設定", padding="5")
        logo_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        logo_frame.columnconfigure(1, weight=1)
        
        ttk.Label(logo_frame, text="Logo URL:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.logo_var = tk.StringVar(value="")
        logo_entry = ttk.Entry(logo_frame, textvariable=self.logo_var, width=30)
        logo_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=3, padx=5)
        
        ttk.Label(logo_frame, text="Logo 模式:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.logoMode_var = tk.StringVar(value="default")
        logoMode_combo = ttk.Combobox(logo_frame, textvariable=self.logoMode_var, values=["default", "clean"], state="readonly", width=10)
        logoMode_combo.grid(row=1, column=1, sticky=tk.W, pady=3, padx=5)
        
        # 儲存按鈕
        save_btn = ttk.Button(config_frame, text="儲存 QR 碼", command=self.save_qr_code)
        save_btn.grid(row=6, column=0, columnspan=2, pady=10)
    
    def create_preview_section(self, parent):
        """建立預覽區域"""
        # 預覽標籤
        self.preview_label = ttk.Label(parent, text="預覽區域", anchor="center")
        self.preview_label.pack(fill="both", expand=True)
    
    def get_config(self):
        """取得配置物件"""
        config = {
            "body": self.body_var.get(),
            "eye": self.eye_var.get(),
            "eyeBall": self.eyeBall_var.get(),
            "bodyColor": self.bodyColor_var.get(),
            "bgColor": self.bgColor_var.get(),
            "eye1Color": self.eye1Color_var.get(),
            "eye2Color": self.eye1Color_var.get(),
            "eye3Color": self.eye1Color_var.get(),
            "eyeBall1Color": self.eyeBall1Color_var.get(),
            "eyeBall2Color": self.eyeBall1Color_var.get(),
            "eyeBall3Color": self.eyeBall1Color_var.get(),
        }
        
        # 漸層設定
        if self.gradientColor1_var.get() and self.gradientColor2_var.get():
            config["gradientColor1"] = self.gradientColor1_var.get()
            config["gradientColor2"] = self.gradientColor2_var.get()
            config["gradientType"] = self.gradientType_var.get()
        
        # Logo 設定
        if self.logo_var.get():
            config["logo"] = self.logo_var.get()
            config["logoMode"] = self.logoMode_var.get()
        
        return config
    
    def generate_qr_code(self):
        """產生 QR 碼"""
        try:
            data = self.url_var.get().strip()
            if not data:
                messagebox.showerror("錯誤", "請輸入網址或文字")
                return
            
            size = self.size_var.get()
            file_format = self.format_var.get()
            config = self.get_config()
            
            # 顯示載入訊息
            self.preview_label.config(text="正在產生 QR 碼...")
            self.root.update()
            
            # 呼叫 API
            qr_data = self.api.create_custom_qr_code(
                data=data,
                size=size,
                config=config,
                file_format=file_format
            )
            
            self.current_qr_data = qr_data
            
            # 如果是 PNG 格式，顯示預覽
            if file_format == "png":
                image = Image.open(io.BytesIO(qr_data))
                # 調整圖片大小以適合預覽
                max_size = 400
                image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                self.preview_label.config(image=photo, text="")
                self.preview_label.image = photo  # 保持引用
                self.qr_image = image
            else:
                self.preview_label.config(text=f"QR 碼已產生 ({file_format} 格式)\n點擊「儲存 QR 碼」按鈕儲存")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"產生 QR 碼時發生錯誤：{str(e)}")
            self.preview_label.config(text="產生失敗")
    
    def save_qr_code(self):
        """儲存 QR 碼"""
        if not self.current_qr_data:
            messagebox.showwarning("警告", "請先產生 QR 碼")
            return
        
        try:
            file_format = self.format_var.get()
            file_ext = file_format
            
            filename = filedialog.asksaveasfilename(
                defaultextension=f".{file_ext}",
                filetypes=[(f"{file_ext.upper()} 檔案", f"*.{file_ext}"), ("所有檔案", "*.*")]
            )
            
            if filename:
                with open(filename, "wb") as f:
                    f.write(self.current_qr_data)
                messagebox.showinfo("成功", f"QR 碼已儲存至：{filename}")
                
        except Exception as e:
            messagebox.showerror("錯誤", f"儲存 QR 碼時發生錯誤：{str(e)}")


def main():
    """主函數"""
    root = tk.Tk()
    app = QRCodeGeneratorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

