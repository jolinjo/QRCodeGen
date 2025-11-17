# QR 碼產生器

這是一個使用 [QRCode Monkey API](https://www.qrcode-monkey.com/qr-code-api-with-logo/) 的 QR 碼產生器專案，目前提供三種執行方式：

1. **Web 版（推薦）**：直接在瀏覽器中開啟 `web/index.html`。
2. **Chrome 擴充功能（雲端 API）**：`chrome-extension/`，呼叫 QRCode Monkey。
3. **Chrome 擴充功能（本地 Python）**：`chrome-extension-local/`，需先啟動 Flask 服務後使用。
4. **離線 CLI 工具**：`offline_generator/`，可在本地端產生 QR 碼且不依賴 API。
5. **Python GUI 應用程式**：位於 `src/`，可作為桌面程式執行。

## 功能特色（Web 版）

- 📱 單頁應用介面，無需安裝擴充功能
- 🔗 支援網址與文字輸入
- 🎨 固定美觀樣式（鑽石身體、Frame 12 眼睛、Ball 14 眼球，經典黑白配色）
- 💾 支援 PNG、SVG、EPS 等輸出格式
- 👁️ 即時預覽（PNG）
- ⬇️ 一鍵下載產生的檔案

## 專案結構

```
python_project/
├── web/                 # 建議使用的 Web 版
│   ├── index.html
│   ├── style.css
│   └── app.js
├── chrome-extension/    # 保留的 Chrome 擴充功能
│   ├── manifest.json
│   ├── background.js
│   ├── page.html
│   ├── page.css
│   ├── page.js
│   ├── icons/
│   └── README.md
├── offline_generator/   # 離線 CLI 工具
│   ├── generate_qr.py
│   └── README.md
├── src/                 # Python GUI 應用程式
│   ├── main.py
│   ├── qr_api.py
│   └── qr_gui.py
├── tests/
├── requirements.txt
└── README.md
```

## Web 版（推薦）

1. 開啟 `web/index.html`（直接用瀏覽器開啟即可）
2. 輸入欲轉換的網址或文字
3. 選擇輸出大小（100-1000），可選擇是否上傳 Logo（PNG / JPG / SVG）
4. 點擊「產生 QR 碼」
5. 產生後可下載 PNG / SVG / EPS 檔案

> 若需部署，可將 `web/` 目錄整體放置於靜態網站伺服器或 CDN。

## Chrome 擴充功能（選用）

若仍需使用擴充功能版本，可參考 `chrome-extension/README.md` 內的安裝與使用說明。該版本同樣使用固定樣式。

## Python GUI 應用程式

### 安裝

1. 確保已安裝 Python 3.8 或更高版本
2. 安裝依賴套件：
   ```bash
   pip install -r requirements.txt
   ```

### 執行

```bash
python src/main.py
```

> 注意：Python GUI 版在 macOS 26+ 可能有相容性問題，建議優先使用 Web 版。

## API 說明

本專案使用 QRCode Monkey 官方 API。若需更進階的造型客製化或自訂 API Key（如經由 RapidAPI），請參考官方文件並調整 `app.js` 或 `popup.js` 中的請求設定。

## 授權

MIT License
