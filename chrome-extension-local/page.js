function extractMetadata() {
  const text = els.data.value;
  const result = { filename: null, cycle: null };
  if (!text) {
    return result;
  }

  let material = null;
  let lot = null;
  let date = null;
  let cycleStr = null;

  try {
    const url = new URL(text.trim());
    const params = url.searchParams;
    material = params.get('material') || material;
    lot = params.get('lot') || lot;
    date = params.get('date') || date;
    cycleStr = params.get('cycle') || cycleStr;
  } catch (err) {
    // ignore parse errors
  }

  if (!material) {
    const match = text.match(/material=([^&\s]+)/i);
    if (match) material = match[1];
  }
  if (!lot) {
    const match = text.match(/lot=([^&\s]+)/i);
    if (match) lot = match[1];
  }
  if (!date) {
    const match = text.match(/date=([^&\s]+)/i);
    if (match) date = match[1];
  }
  if (!cycleStr) {
    const match = text.match(/cycle=([^&\s]+)/i);
    if (match) cycleStr = match[1];
  }

  if (cycleStr) {
    const parsed = parseInt(cycleStr, 10);
    if (!Number.isNaN(parsed) && parsed >= 1) {
      result.cycle = parsed;
    }
  }

  if (material && lot && date && cycleStr) {
    result.filename = `${material}-${lot}-${date}-${cycleStr}`;
  }

  return result;
}

async function loadCycleLogo(cycle) {
  const url = chrome.runtime.getURL(`logos/${cycle}.svg`);
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`載入預設 Logo 失敗 (${cycle})`);
  }
  const text = await res.text();
  const base64 = btoa(unescape(encodeURIComponent(text)));
  return `data:image/svg+xml;base64,${base64}`;
}
const API_URL = 'http://127.0.0.1:5002/generate';

// 容錯率對應的最大 logo 比例
const ERROR_LEVEL_MAX_LOGO_SCALE = {
  L: 0.07,  // 7%
  M: 0.15,  // 15%
  Q: 0.25,  // 25%
  H: 0.30,  // 30%
};

// 獲取當前容錯率對應的最大 logo 比例
function getMaxLogoScale() {
  const errorLevel = (els.errorLevel.value || 'Q').toUpperCase();
  return ERROR_LEVEL_MAX_LOGO_SCALE[errorLevel] || 0.25;
}

// 更新 logo 比例輸入框的最大值和當前值
function updateLogoScaleLimit() {
  const maxScale = getMaxLogoScale();
  els.logoScale.max = maxScale.toFixed(2);
  
  // 如果當前值超過新的最大值，自動調整
  const currentValue = parseFloat(els.logoScale.value);
  if (!Number.isNaN(currentValue) && currentValue > maxScale) {
    els.logoScale.value = maxScale.toFixed(2);
    setMessage(
      `⚠️ 容錯率 ${els.errorLevel.value} 的最大 Logo 比例為 ${(maxScale * 100).toFixed(0)}%，已自動調整為 ${(maxScale * 100).toFixed(0)}%`,
      'error'
    );
    // 3 秒後清除訊息
    setTimeout(() => {
      if (els.message.textContent.includes('已自動調整')) {
        setMessage('', '');
      }
    }, 3000);
  }
}

const els = {
  status: document.getElementById('server-status'),
  data: document.getElementById('qr-data'),
  scale: document.getElementById('scale'),
  errorLevel: document.getElementById('error-level'),
  logo: document.getElementById('logo'),
  logoScale: document.getElementById('logo-scale'),
  qrWidth: document.getElementById('qr-width'),
  qrHeight: document.getElementById('qr-height'),
  button: document.getElementById('generate-btn'),
  message: document.getElementById('message'),
  metaInfo: document.getElementById('meta-info'),
  metaVersion: document.getElementById('meta-version'),
  metaModuleSize: document.getElementById('meta-module-size'),
  metaQrSize: document.getElementById('meta-qr-size'),
  metaClearArea: document.getElementById('meta-clear-area'),
  previewContainer: document.getElementById('preview-container'),
  previewImage: document.getElementById('preview'),
  downloadSvg: document.getElementById('download-svg'),
  previewTableContainer: document.getElementById('preview-table-container'),
  previewTableBody: document.getElementById('preview-table-body'),
  currentCharCount: document.getElementById('current-char-count'),
};

async function checkServer() {
  try {
    const res = await fetch(API_URL, { method: 'OPTIONS' });
    if (res.ok) {
      els.status.textContent = '連線正常';
      els.status.classList.remove('status-off');
      els.status.classList.add('status-on');
    } else {
      throw new Error('status ' + res.status);
    }
  } catch (err) {
    els.status.textContent = '未連線';
    els.status.classList.remove('status-on');
    els.status.classList.add('status-off');
  }
}

async function readFileAsDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function setMessage(text, type = '') {
  els.message.textContent = text;
  els.message.className = type;
}

let svgBlobUrl = null;

function resetResult() {
  els.previewContainer.classList.add('hidden');
  els.previewImage.src = '';
  els.downloadSvg.classList.add('disabled');
  els.downloadSvg.removeAttribute('href');
  els.downloadSvg.removeAttribute('download');
  els.downloadSvg.textContent = '下載 SVG';
  els.metaInfo.classList.add('hidden');
  els.metaVersion.textContent = '';
  els.metaModuleSize.textContent = '';
  els.metaQrSize.textContent = '';
  els.metaClearArea.textContent = '';
  
  // 清理舊的 blob URL
  if (svgBlobUrl) {
    URL.revokeObjectURL(svgBlobUrl);
    svgBlobUrl = null;
  }
}

async function generate() {
  resetResult();
  const data = els.data.value.trim();
  if (!data) {
    setMessage('請輸入要編碼的文字或網址', 'error');
    return;
  }

  const basePayload = {
    data,
    scale: Number(els.scale.value) || 8,
    border: 0,
    dark: '#000000',
    light: '#ffffff',
    errorLevel: (els.errorLevel.value || 'Q').toUpperCase(),
  };
  const metadata = extractMetadata();
  const extracted = metadata.filename;
  const cycleNumber = metadata.cycle;

  // 檢查 logo 比例是否超過容錯率限制
  const maxLogoScale = getMaxLogoScale();
  const logoRatio = parseFloat(els.logoScale.value);
  
  if (!Number.isNaN(logoRatio)) {
    if (logoRatio > maxLogoScale) {
      setMessage(
        `Logo 比例 (${(logoRatio * 100).toFixed(0)}%) 超過容錯率 ${els.errorLevel.value} 的最大值 (${(maxLogoScale * 100).toFixed(0)}%)，請調整 Logo 比例或提高容錯率`,
        'error'
      );
      return;
    }
    const clamped = Math.min(Math.max(logoRatio, 0), maxLogoScale);
    basePayload.logoScale = clamped;
    if (clamped !== logoRatio) {
      els.logoScale.value = clamped.toFixed(2);
    }
  } else {
    // 如果輸入無效，使用預設值（但不超過最大值）
    const defaultScale = Math.min(0.3, maxLogoScale);
    basePayload.logoScale = defaultScale;
    els.logoScale.value = defaultScale.toFixed(2);
  }

  const widthMm = parseFloat(els.qrWidth.value);
  const heightMm = parseFloat(els.qrHeight.value);
  const DEFAULT_QR_MM = 16.5;
  basePayload.qrWidthMm = !Number.isNaN(widthMm) && widthMm > 0 ? widthMm : DEFAULT_QR_MM;
  basePayload.qrHeightMm = !Number.isNaN(heightMm) && heightMm > 0 ? heightMm : DEFAULT_QR_MM;
  if (Number.isNaN(widthMm) || widthMm <= 0) {
    els.qrWidth.value = DEFAULT_QR_MM.toFixed(1);
  }
  if (Number.isNaN(heightMm) || heightMm <= 0) {
    els.qrHeight.value = DEFAULT_QR_MM.toFixed(1);
  }

  const file = els.logo.files?.[0];
  if (file) {
    const isSvg =
      file.type === 'image/svg+xml' ||
      file.name.toLowerCase().endsWith('.svg');
    if (!isSvg) {
      setMessage('請上傳 SVG 檔案作為 Logo', 'error');
      return;
    }
    basePayload.logo = await readFileAsDataURL(file);
  } else if (cycleNumber && cycleNumber >= 1 && cycleNumber <= 5) {
    try {
      basePayload.logo = await loadCycleLogo(cycleNumber);
    } catch (err) {
      console.error(err);
    }
  }

  try {
    els.button.disabled = true;
    setMessage('產生中...', '');

    // 產生 SVG
    const svgPayload = { ...basePayload, format: 'svg' };
    
    if (extracted) {
      svgPayload.filename = `${extracted}.svg`;
    }

    const svgResponse = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(svgPayload),
    });

    const svgResult = await svgResponse.json();

    if (!svgResponse.ok || svgResult.status !== 'ok') {
      throw new Error(svgResult.message || '無法產生 SVG QR Code');
    }

    setMessage('產生成功！SVG 檔案已準備下載。', 'success');

    // 顯示元資料（使用 SVG 的元資料）
    if (svgResult.metadata) {
      const version = svgResult.metadata.version ?? '?';
      const modules = svgResult.metadata.modules_per_side ?? '?';
      const moduleSize = svgResult.metadata.module_size ?? '?';
      const moduleSizeMm = svgResult.metadata.module_size_mm ?? null;
      const qrWidthMm = svgResult.metadata.qr_width_mm ?? null;
      const qrHeightMm = svgResult.metadata.qr_height_mm ?? null;
      const clearSizeMm = svgResult.metadata.clear_area_mm ?? null;

      els.metaVersion.textContent = `版本：${version}（模組：${modules}×${modules}）`;
      els.metaModuleSize.textContent = moduleSizeMm
        ? `單點尺寸：約 ${parseFloat(moduleSizeMm).toFixed(2)} mm（像素：${moduleSize}）`
        : `單點尺寸（像素）：${moduleSize}`;
      els.metaQrSize.textContent = qrWidthMm && qrHeightMm
        ? `整體尺寸：約 ${parseFloat(qrWidthMm).toFixed(1)} mm × ${parseFloat(qrHeightMm).toFixed(1)} mm`
        : '整體尺寸：使用預設值';
      els.metaClearArea.textContent = clearSizeMm
        ? `中央留白：約 ${parseFloat(clearSizeMm).toFixed(1)} mm`
        : '中央留白：未設定';

      els.metaInfo.classList.remove('hidden');
    }

    // 處理 SVG
    const svgByteString = atob(svgResult.data);
    const svgArrayBuffer = new ArrayBuffer(svgByteString.length);
    const svgUintArray = new Uint8Array(svgArrayBuffer);
    for (let i = 0; i < svgByteString.length; i += 1) {
      svgUintArray[i] = svgByteString.charCodeAt(i);
    }
    const svgBlob = new Blob([svgArrayBuffer], { type: svgResult.mime });
    svgBlobUrl = URL.createObjectURL(svgBlob);

    const svgDownloadBase = svgResult.filename
      ? svgResult.filename.replace(/\.[^.]+$/, '')
      : extracted ?? 'qrcode';
    els.downloadSvg.href = svgBlobUrl;
    els.downloadSvg.download = `${svgDownloadBase}.svg`;
    els.downloadSvg.classList.remove('disabled');
    els.downloadSvg.textContent = '下載 SVG';

    // 使用 SVG 預覽
    els.previewImage.src = svgBlobUrl;
    els.previewContainer.classList.remove('hidden');
  } catch (error) {
    console.error(error);
    setMessage(error.message || '產生過程發生錯誤', 'error');
  } finally {
    els.button.disabled = false;
  }
}

els.button.addEventListener('click', () => {
  generate();
});

// Debounce 函數
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// 更新預覽表格
function updatePreviewTable(previewData) {
  if (!previewData || !previewData.preview || previewData.preview.length === 0) {
    els.previewTableContainer.classList.add('hidden');
    return;
  }

  // 更新字數顯示
  const dataLength = previewData.data ? previewData.data.length : 0;
  els.currentCharCount.textContent = dataLength.toLocaleString();

  els.previewTableBody.innerHTML = '';
  
  previewData.preview.forEach((item) => {
    const row = document.createElement('tr');
    
    if (item.error) {
      row.innerHTML = `
        <td>${item.error_level}</td>
        <td colspan="7" class="error-cell">錯誤: ${item.error}</td>
      `;
    } else {
      const errorLevelName = {
        L: 'L (7%)',
        M: 'M (15%)',
        Q: 'Q (25%)',
        H: 'H (30%)',
      }[item.error_level] || item.error_level;
      
      // 計算並顯示剩餘容錯區域
      let remainingErrorCell = '-';
      if (item.remaining_error_margin !== undefined) {
        const remainingPercent = (item.remaining_error_margin * 100).toFixed(1);
        // 如果剩餘容錯區域太小，用警告樣式顯示
        const cellClass = item.remaining_error_margin < 0.05 ? 'warning-cell' : '';
        remainingErrorCell = `<span class="${cellClass}">${remainingPercent}%</span>`;
      }
      
      // 顯示冗餘資料量
      const redundantDataCell = item.redundant_data !== undefined && item.redundant_data !== null
        ? item.redundant_data.toLocaleString()
        : '-';
      
      row.innerHTML = `
        <td>${errorLevelName}</td>
        <td>${item.version || '-'}</td>
        <td>${item.modules_per_side || '-'}×${item.modules_per_side || '-'}</td>
        <td>${item.module_size_mm ? parseFloat(item.module_size_mm).toFixed(2) : '-'}</td>
        <td>${item.clear_area_mm ? parseFloat(item.clear_area_mm).toFixed(2) : '-'}</td>
        <td>${item.max_capacity ? item.max_capacity.toLocaleString() : '-'}</td>
        <td>${remainingErrorCell}</td>
        <td>${redundantDataCell}</td>
      `;
    }
    
    els.previewTableBody.appendChild(row);
  });

  els.previewTableContainer.classList.remove('hidden');
}

// 調用預覽 API
async function fetchPreview() {
  const data = els.data.value.trim();
  if (!data) {
    els.previewTableContainer.classList.add('hidden');
    return;
  }

  try {
    const scale = Number(els.scale.value) || 8;
    const qrWidthMm = parseFloat(els.qrWidth.value) || 16.5;
    const qrHeightMm = parseFloat(els.qrHeight.value) || 16.5;

    // 獲取當前的 logo 比例
    const logoScale = parseFloat(els.logoScale.value) || 0;
    
    const response = await fetch('http://127.0.0.1:5002/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        data,
        scale,
        border: 0,
        qrWidthMm,
        qrHeightMm,
        logoScale,
      }),
    });

    const result = await response.json();

    if (response.ok && result.status === 'ok') {
      updatePreviewTable(result);
    } else {
      els.previewTableContainer.classList.add('hidden');
    }
  } catch (error) {
    console.error('預覽失敗:', error);
    els.previewTableContainer.classList.add('hidden');
  }
}

// 使用 debounce 包裝預覽函數，延遲 500ms
const debouncedFetchPreview = debounce(fetchPreview, 500);

// 監聽輸入內容變化
els.data.addEventListener('input', () => {
  debouncedFetchPreview();
});

// 監聽 QR 寬度和高度變化
els.qrWidth.addEventListener('input', () => {
  debouncedFetchPreview();
});

els.qrHeight.addEventListener('input', () => {
  debouncedFetchPreview();
});

// 監聽模組大小變化
els.scale.addEventListener('input', () => {
  debouncedFetchPreview();
});

// 監聽 logo 比例變化
els.logoScale.addEventListener('input', () => {
  debouncedFetchPreview();
});

// 監聽容錯率變化，動態調整 logo 比例的最大值
els.errorLevel.addEventListener('change', () => {
  updateLogoScaleLimit();
  debouncedFetchPreview();
});

// 頁面載入時初始化 logo 比例的最大值
updateLogoScaleLimit();

checkServer();
setInterval(checkServer, 5000);
