# QR 碼產生器 Chrome 擴充功能

這是一個 Chrome 擴充功能，整合 [QRCode Monkey API](https://www.qrcode-monkey.com/qr-code-api-with-logo/)，可以快速在新分頁中產生固定樣式的 QR 碼：

- 鑽石身體（diamond）
- Frame 12 眼睛
- Ball 14 眼球
- 經典黑白配色
- Logo 可上傳（PNG/JPG/SVG）並嵌入 QR 碼

## 使用方式

1. 安裝擴充功能（開發者模式 → `載入未封裝項目` → 選擇 `chrome-extension/` 資料夾）。
2. 點擊工具列上的擴充功能圖示。
3. 擴充功能會在新分頁開啟完整介面：
   - 輸入欲轉換的網址或文字
   - 選擇 QR 碼大小（100-1000 像素）；產生後可下載 PNG / SVG / EPS
   - 點擊「產生 QR 碼」→ 可預覽或下載 PNG / SVG / EPS（支援上傳 Logo）
4. 可選擇是否上傳 Logo（PNG / JPG / SVG），未上傳時會產生純黑白樣式。
5. 所有設定（網址、大小、格式）會自動保存至 `chrome.storage.sync`，下次開啟會自動帶入。

## 檔案結構

```
chrome-extension/
├── manifest.json      # 擴充功能配置
├── background.js      # 監聽圖示點擊並開啟專用分頁
├── page.html          # 主頁面
├── page.css           # 樣式
├── page.js            # 主要邏輯（含 API 呼叫）
├── icons/             # 圖標（需保留三種尺寸）
└── README.md
```

## API 說明

本擴充功能預設呼叫官方 API（`https://api.qrcode-monkey.com/qr/custom`）。若需改用 RapidAPI 或自訂金鑰，請編輯 `page.js` 中的 `fetch` 呼叫，加入必要的 headers。

```javascript
fetch('https://qrcode-monkey.p.rapidapi.com/qr/custom', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-RapidAPI-Key': '你的 API Key',
    'X-RapidAPI-Host': 'qrcode-monkey.p.rapidapi.com'
  },
  body: JSON.stringify(payload)
});
```

## 開發與除錯

1. 開啟 `chrome://extensions/`
2. 啟用「開發人員模式」
3. 重新載入擴充功能（🔄）即可套用修改
4. 點擊「服務工作器」的 `檢查檢視`，查看 `background.js` 日誌
5. 在打開的 QR 碼頁面（`page.html`）中使用 DevTools (F12) 觀察 Console 與 Network

## 授權

MIT License
