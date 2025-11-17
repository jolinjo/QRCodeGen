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

const els = {
  status: document.getElementById('server-status'),
  data: document.getElementById('qr-data'),
  format: document.getElementById('format'),
  scale: document.getElementById('scale'),
  border: document.getElementById('border'),
  dark: document.getElementById('dark'),
  light: document.getElementById('light'),
  errorLevel: document.getElementById('error-level'),
  logo: document.getElementById('logo'),
  logoScale: document.getElementById('logo-scale'),
  qrWidth: document.getElementById('qr-width'),
  qrHeight: document.getElementById('qr-height'),
  button: document.getElementById('generate-btn'),
  buttonAi: document.getElementById('generate-ai-btn'),
  message: document.getElementById('message'),
  metaInfo: document.getElementById('meta-info'),
  metaVersion: document.getElementById('meta-version'),
  metaModuleSize: document.getElementById('meta-module-size'),
  metaQrSize: document.getElementById('meta-qr-size'),
  metaClearArea: document.getElementById('meta-clear-area'),
  previewContainer: document.getElementById('preview-container'),
  previewImage: document.getElementById('preview'),
  download: document.getElementById('download-link'),
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

function resetResult() {
  els.previewContainer.classList.add('hidden');
  els.previewImage.src = '';
  els.download.classList.add('disabled');
  els.download.removeAttribute('href');
  els.download.removeAttribute('download');
  els.download.textContent = '下載檔案';
  els.metaInfo.classList.add('hidden');
  els.metaVersion.textContent = '';
  els.metaModuleSize.textContent = '';
  els.metaQrSize.textContent = '';
  els.metaClearArea.textContent = '';
}

async function generate(forcedFormat = null) {
  resetResult();
  const data = els.data.value.trim();
  if (!data) {
    setMessage('請輸入要編碼的文字或網址', 'error');
    return;
  }

  const format = forcedFormat || els.format.value;

  const payload = {
    data,
    format,
    scale: Number(els.scale.value) || 8,
    border: Number(els.border.value) || 4,
    dark: els.dark.value || '#000000',
    light: els.light.value || '#ffffff',
    errorLevel: (els.errorLevel.value || 'L').toUpperCase(),
  };
  const metadata = extractMetadata();
  const extracted = metadata.filename;
  const cycleNumber = metadata.cycle;
  if (extracted) {
    payload.filename = `${extracted}.${format}`;
  }

  const logoRatio = parseFloat(els.logoScale.value);
  if (!Number.isNaN(logoRatio)) {
    const clamped = Math.min(Math.max(logoRatio, 0), 0.4);
    payload.logoScale = clamped;
    if (clamped !== logoRatio) {
      els.logoScale.value = clamped.toFixed(2);
    }
  } else {
    payload.logoScale = 0.3;
    els.logoScale.value = '0.30';
  }

  const widthMm = parseFloat(els.qrWidth.value);
  const heightMm = parseFloat(els.qrHeight.value);
  const DEFAULT_QR_MM = 16.5;
  payload.qrWidthMm = !Number.isNaN(widthMm) && widthMm > 0 ? widthMm : DEFAULT_QR_MM;
  payload.qrHeightMm = !Number.isNaN(heightMm) && heightMm > 0 ? heightMm : DEFAULT_QR_MM;
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
    payload.logo = await readFileAsDataURL(file);
  } else if (cycleNumber && cycleNumber >= 1 && cycleNumber <= 5) {
    try {
      payload.logo = await loadCycleLogo(cycleNumber);
    } catch (err) {
      console.error(err);
    }
  }

  try {
    els.button.disabled = true;
    if (els.buttonAi) {
      els.buttonAi.disabled = true;
    }
    setMessage('產生中...', '');

    const response = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const result = await response.json();

    if (!response.ok || result.status !== 'ok') {
      throw new Error(result.message || '無法產生 QR Code');
    }

    const label = payload.format.toUpperCase();
    setMessage(`產生成功！${label} 檔案已準備下載。`, 'success');

    if (result.metadata) {
      const version = result.metadata.version ?? '?';
      const modules = result.metadata.modules_per_side ?? '?';
      const moduleSize = result.metadata.module_size ?? '?';
      const moduleSizeMm = result.metadata.module_size_mm ?? null;
      const qrWidthMm = result.metadata.qr_width_mm ?? null;
      const qrHeightMm = result.metadata.qr_height_mm ?? null;
      const clearSizeMm = result.metadata.clear_area_mm ?? null;

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

    const byteString = atob(result.data);
    const arrayBuffer = new ArrayBuffer(byteString.length);
    const uintArray = new Uint8Array(arrayBuffer);
    for (let i = 0; i < byteString.length; i += 1) {
      uintArray[i] = byteString.charCodeAt(i);
    }
    const blob = new Blob([arrayBuffer], { type: result.mime });
    const url = URL.createObjectURL(blob);

    els.download.href = url;
    const downloadBase = result.filename
      ? result.filename.replace(/\.[^.]+$/, '')
      : extracted ?? 'qrcode';
    els.download.download = `${downloadBase}.${payload.format}`;
    els.download.classList.remove('disabled');
    els.download.textContent = `下載 ${label}`;

    if (payload.format === 'svg') {
      els.previewImage.src = url;
      els.previewContainer.classList.remove('hidden');
    } else {
      els.previewContainer.classList.add('hidden');
      els.previewImage.src = '';
    }
  } catch (error) {
    console.error(error);
    setMessage(error.message || '產生過程發生錯誤', 'error');
  } finally {
    els.button.disabled = false;
    if (els.buttonAi) {
      els.buttonAi.disabled = false;
    }
  }
}

els.button.addEventListener('click', () => {
  generate();
});

if (els.buttonAi) {
  els.buttonAi.addEventListener('click', () => {
    generate('ai');
  });
}

checkServer();
setInterval(checkServer, 5000);
