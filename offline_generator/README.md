# Offline QR Code Generator

這是一個不依賴任何雲端 API 的 QR Code 產生工具。

使用 [segno](https://pypi.org/project/segno/) 套件在本地端生成 QR 碼，可輸出 `PNG / SVG / EPS / PDF / DXF / AI`，並支援在中心區域放置 SVG Logo、設定整體 QR 寬度／高度（毫米）以及選擇容錯率。

## 安裝

```bash
python3 -m pip install segno pillow cairosvg ezdxf
```

## 使用方式

```bash
python offline_generator/generate_qr.py "https://example.com" output.png
```

可用參數：

| 參數 | 說明 | 預設值 |
| --- | --- | --- |
| `--scale` | 單一模組像素大小（越大圖片越大） | 8 |
| `--border` | 邊框寬度（單位：模組） | 4 |
| `--dark` | 深色模組顏色（HEX） | `#000000` |
| `--light` | 淺色背景顏色（HEX） | `#ffffff` |
| `--logo` | Logo 圖片路徑（僅 PNG 支援疊加） | 無 |
| `--logo-scale` | Logo 寬度與 QR 寬度比例（0.05 ~ 0.5） | 0.22 |
| `--quiet` | 不輸出進度訊息 | False |

範例：

```bash
# 產生 SVG
python offline_generator/generate_qr.py "Hello World" hello.svg --scale 10

# 產生帶 Logo 的 PNG
python offline_generator/generate_qr.py "https://example.com" site.png --logo my_logo.png --logo-scale 0.18

# 產生 EPS
python offline_generator/generate_qr.py "WiFi network" wifi.eps --scale 6
```

> 注意：若要在 PNG 上加入 SVG Logo，需額外安裝 `cairosvg` 進行轉換。

## Streamlit UI

```bash
streamlit run offline_generator/app_streamlit.py
```

## Gradio UI

```bash
python offline_generator/app_gradio.py
```

## Flask API Server

```bash
python3 -m pip install flask segno pillow cairosvg ezdxf
python3 offline_generator/server_flask.py --port 5001
```

POST /generate 範例 JSON：

```json
{
  "data": "https://example.com",
  "format": "png",
  "scale": 8,
  "border": 4,
  "dark": "#000000",
  "light": "#ffffff",
  "errorLevel": "L",
  "logo": null,
  "logoScale": 0.3,
  "qrWidthMm": 16.5,
  "qrHeightMm": 16.5
}
```

伺服器會回傳 Base64 編碼的 QR 碼（已將模組轉換成菱形，定位點為圓形）。支援 `PNG / SVG / EPS / PDF / DXF / AI`，若提供 `logo` 需為 SVG 檔，會自動縮放到中央留白區域並依 QR 寬高換算的模組尺寸置中。回應 `metadata` 中會包含版本、模組數、單點尺寸（像素與毫米）以及 QR 實際寬高：

```json
{
  "status": "ok",
  "filename": "qrcode.png",
  "mime": "image/png",
  "data": "iVBORw0...",
  "metadata": {
    "version": 4,
    "modules_per_side": 33,
    "module_size": 8,
    "module_size_mm": 0.5,
  "qr_width_mm": 16.5,
  "qr_height_mm": 16.5,
  "clear_area_mm": 8.3
  }
}
```
