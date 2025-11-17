#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QRCode Monkey API 客戶端
"""

import requests
from typing import Dict, Optional, BinaryIO
import io
from PIL import Image


class QRCodeMonkeyAPI:
    """QRCode Monkey API 客戶端類別"""
    
    # API 基礎 URL
    BASE_URL = "https://api.qrcode-monkey.com"
    RAPIDAPI_URL = "https://qrcode-monkey.p.rapidapi.com"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 API 客戶端
        
        Args:
            api_key: API 金鑰（如果需要通過 RapidAPI）
        """
        self.api_key = api_key
        self.base_url = self.RAPIDAPI_URL if api_key else self.BASE_URL
        self.headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            self.headers["X-RapidAPI-Key"] = api_key
            self.headers["X-RapidAPI-Host"] = "qrcode-monkey.p.rapidapi.com"
    
    def create_custom_qr_code(
        self,
        data: str,
        size: int = 300,
        config: Optional[Dict] = None,
        file_format: str = "png",
        download: bool = False
    ) -> bytes:
        """
        建立自訂 QR 碼
        
        Args:
            data: QR 碼內容（如 URL）
            size: QR 碼最小像素大小
            config: 客製化配置物件
            file_format: 輸出檔案格式 (png, svg, pdf, eps)
            download: 是否強制下載
            
        Returns:
            QR 碼圖片的二進位資料
        """
        if config is None:
            config = {}
        
        url = f"{self.base_url}/qr/custom"
        
        payload = {
            "data": data,
            "size": size,
            "config": config,
            "file": file_format,
            "download": download
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # 檢查回應內容類型
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                # 如果返回 JSON，可能是錯誤訊息
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', '未知錯誤')
                    raise Exception(f"API 錯誤: {error_msg}")
                except:
                    pass
            
            return response.content
        except requests.exceptions.Timeout:
            raise Exception("API 請求超時，請稍後再試")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"API 請求失敗 (HTTP {e.response.status_code}): {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"API 請求失敗: {str(e)}")
    
    def create_transparent_qr_code(
        self,
        data: str,
        image: Optional[str] = None,
        size: int = 300,
        x: int = 0,
        y: int = 0,
        crop: bool = False,
        file_format: str = "png",
        download: bool = False
    ) -> bytes:
        """
        建立透明 QR 碼
        
        Args:
            data: QR 碼內容
            image: 背景圖片 URL 或檔案名稱
            size: QR 碼寬高
            x: QR 碼在圖片上的 x 位置
            y: QR 碼在圖片上的 y 位置
            crop: 是否只返回 QR 碼（不包含周圍圖片）
            file_format: 輸出檔案格式
            download: 是否強制下載
            
        Returns:
            QR 碼圖片的二進位資料
        """
        url = f"{self.base_url}/qr/transparent"
        
        payload = {
            "data": data,
            "size": size,
            "x": x,
            "y": y,
            "crop": crop,
            "file": file_format,
            "download": download
        }
        
        if image:
            payload["image"] = image
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # 檢查回應內容類型
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                # 如果返回 JSON，可能是錯誤訊息
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', '未知錯誤')
                    raise Exception(f"API 錯誤: {error_msg}")
                except:
                    pass
            
            return response.content
        except requests.exceptions.Timeout:
            raise Exception("API 請求超時，請稍後再試")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"API 請求失敗 (HTTP {e.response.status_code}): {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"API 請求失敗: {str(e)}")
    
    def upload_image(self, image_file: BinaryIO) -> str:
        """
        上傳圖片作為 logo
        
        Args:
            image_file: 圖片檔案物件
            
        Returns:
            上傳後的檔案名稱
        """
        url = f"{self.base_url}/qr/uploadImage"
        
        files = {"file": image_file}
        
        try:
            # 上傳檔案時不需要 JSON header
            upload_headers = {}
            if self.api_key:
                upload_headers["X-RapidAPI-Key"] = self.api_key
                upload_headers["X-RapidAPI-Host"] = "qrcode-monkey.p.rapidapi.com"
            
            response = requests.post(url, files=files, headers=upload_headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result.get("file", "")
        except requests.exceptions.Timeout:
            raise Exception("圖片上傳超時，請稍後再試")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"圖片上傳失敗 (HTTP {e.response.status_code}): {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"圖片上傳失敗: {str(e)}")
    
    def get_qr_image(self, data: str, config: Optional[Dict] = None, size: int = 300) -> Image.Image:
        """
        獲取 QR 碼圖片物件
        
        Args:
            data: QR 碼內容
            config: 客製化配置
            size: QR 碼大小
            
        Returns:
            PIL Image 物件
        """
        qr_data = self.create_custom_qr_code(data, size, config, "png")
        return Image.open(io.BytesIO(qr_data))

