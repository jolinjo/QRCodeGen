# QR 碼產生器（精簡版）

一個使用 Python 本地服務產生 QR 碼的 Chrome 擴充功能。不依賴任何雲端 API，所有處理都在本地完成。

## 功能特色

- 🐍 **本地 Python 服務**：使用 Flask + segno 在本地產生 QR 碼
- 🎨 **客製化樣式**：菱形模組、圓形定位點
- 📐 **尺寸控制**：可設定 QR 碼整體尺寸（mm）、中央留白比例
- 🖼️ **Logo 支援**：自動載入 SVG Logo（可依 cycle 參數自動選擇）
- 📊 **多格式輸出**：支援 SVG、DXF、AI（Illustrator 8）格式
- 📏 **詳細資訊顯示**：版本、模組數、單點尺寸、QR 尺寸、中央留白尺寸

## 專案結構

```
QRCodeGen/
├── chrome-extension-local/    # Chrome 擴充功能 GUI
│   ├── manifest.json
│   ├── background.js
│   ├── page.html
│   ├── page.css
│   ├── page.js
│   ├── logos/                 # 預設 Logo（1.svg ~ 5.svg）
│   └── README.md
├── offline_generator/         # Python 本地服務
│   ├── server_flask.py        # Flask API 伺服器
│   └── README.md
├── requirements.txt           # Python 依賴套件
└── README.md
```

## 安裝與使用

### 1. 安裝 Python 依賴

```bash
python3 -m pip install -r requirements.txt
```

或使用虛擬環境（建議）：

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 啟動 Flask 服務

```bash
source .venv/bin/activate  # 如果使用虛擬環境
python offline_generator/server_flask.py --port 5002
```

服務會在本機 `http://127.0.0.1:5002` 運行。

### 3. 安裝 Chrome 擴充功能

1. 開啟 Chrome，前往 `chrome://extensions/`
2. 開啟「開發人員模式」（右上角開關）
3. 點擊「載入未封裝項目」
4. 選擇 `chrome-extension-local/` 目錄
5. 擴充功能圖示會出現在工具列

### 4. 使用擴充功能

1. 點擊擴充功能圖示，會開啟新的分頁
2. 輸入要編碼的文字或網址
3. 選擇輸出格式（SVG / DXF / AI）
4. 調整設定：
   - 容錯率（L/M/Q/H，預設 L）
   - QR 寬度/高度（mm）
   - Logo 與 QR 比例（0 ~ 0.4）
   - 上傳 Logo（SVG）或依 cycle 參數自動載入
5. 點擊「產生 QR Code」或「產生 AI」
6. 預覽並下載

## 自動功能

### 自動檔名

如果輸入的網址包含以下參數，會自動組合成檔名：
- `material=...`：材料
- `lot=...`：原料批號
- `date=...`：日期
- `cycle=...`：循環次數

檔名格式：`材料-原料批號-日期-循環次數.格式`

### 自動 Logo

如果網址中有 `cycle=1~5` 且未上傳 Logo，會自動載入 `logos/{cycle}.svg`。

## API 端點

### POST /generate

產生 QR 碼。

**請求範例：**

```json
{
  "data": "https://example.com",
  "format": "svg",
  "scale": 8,
  "border": 4,
  "dark": "#000000",
  "light": "#ffffff",
  "errorLevel": "L",
  "qrWidthMm": 16.5,
  "qrHeightMm": 16.5,
  "logoScale": 0.3,
  "logo": "data:image/svg+xml;base64,..."
}
```

**回應範例：**

```json
{
  "status": "ok",
  "filename": "qrcode.svg",
  "mime": "image/svg+xml",
  "data": "base64_encoded_content...",
  "metadata": {
    "version": 4,
    "modules_per_side": 33,
    "module_size": 8,
    "module_size_mm": 0.5,
    "qr_width_mm": 16.5,
    "qr_height_mm": 16.5,
    "clear_area_mm": 4.95
  }
}
```

## 授權

MIT License