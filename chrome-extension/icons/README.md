# 圖標檔案

請在此目錄下放置以下圖標檔案：

- `icon16.png` - 16x16 像素
- `icon48.png` - 48x48 像素
- `icon128.png` - 128x128 像素

## 快速生成圖標

您可以使用以下線上工具生成圖標：

1. https://www.favicon-generator.org/
2. https://realfavicongenerator.net/
3. https://favicon.io/

或者使用 ImageMagick 等工具從現有圖片生成：

```bash
convert input.png -resize 16x16 icon16.png
convert input.png -resize 48x48 icon48.png
convert input.png -resize 128x128 icon128.png
```

## 臨時解決方案

如果暫時沒有圖標檔案，可以創建簡單的 PNG 檔案，或者修改 `manifest.json` 移除圖標引用（不推薦）。

