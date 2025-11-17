# Chrome 擴充功能：本地 Python QR Code 產生器

此版本專門用來呼叫本地的 Flask 服務 (`offline_generator/server_flask.py`) 產生 QR 碼，不再直接打 QRCode Monkey API。使用步驟：

1. 先啟動本地服務
   ```bash
   python3 -m pip install flask segno pillow cairosvg ezdxf
   python offline_generator/server_flask.py --port 5002
   ```

2. 在 Chrome 中載入擴充功能
   - 打開 `chrome://extensions`
   - 開啟「開發人員模式」
   - 點「載入未封裝項目」，選擇 `chrome-extension-local/`

3. 點擊擴充功能圖示 → 會在新分頁開啟 UI
   - 輸入網址或文字
   - 點擊「產生 QR Code」會同時產生 SVG 和 DXF 格式
   - 可選擇容錯率（L/M/Q/H），上傳 SVG Logo，調整整體 QR 寬/高（mm）與留白比例；若網址包含 `cycle=1~5` 且未上傳 Logo，會自動套用 `logos/` 內對應的預設圖案
   - 產生後可預覽 SVG 或下載 SVG/DXF 檔案（SVG 預覽支援 Logo），結果面板會顯示 QR 版本、模組數、單點尺寸（像素與毫米）、中央留白與 QR 實際毫米大小

> UI 在 `page.html` / `page.css` / `page.js`，若要調整操作行為或欄位，可直接修改這三個檔案。
