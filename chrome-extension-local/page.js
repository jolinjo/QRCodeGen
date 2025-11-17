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
  downloadDxf: document.getElementById('download-dxf'),
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
let dxfBlobUrl = null;

function resetResult() {
  els.previewContainer.classList.add('hidden');
  els.previewImage.src = '';
  els.downloadSvg.classList.add('disabled');
  els.downloadDxf.classList.add('disabled');
  els.downloadSvg.removeAttribute('href');
  els.downloadDxf.removeAttribute('href');
  els.downloadSvg.removeAttribute('download');
  els.downloadDxf.removeAttribute('download');
  els.downloadSvg.textContent = '下載 SVG';
  els.downloadDxf.textContent = '下載 DXF';
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
  if (dxfBlobUrl) {
    URL.revokeObjectURL(dxfBlobUrl);
    dxfBlobUrl = null;
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
    errorLevel: (els.errorLevel.value || 'L').toUpperCase(),
  };
  const metadata = extractMetadata();
  const extracted = metadata.filename;
  const cycleNumber = metadata.cycle;

  const logoRatio = parseFloat(els.logoScale.value);
  if (!Number.isNaN(logoRatio)) {
    const clamped = Math.min(Math.max(logoRatio, 0), 0.4);
    basePayload.logoScale = clamped;
    if (clamped !== logoRatio) {
      els.logoScale.value = clamped.toFixed(2);
    }
  } else {
    basePayload.logoScale = 0.3;
    els.logoScale.value = '0.30';
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

    // 同時產生 SVG 和 DXF
    const svgPayload = { ...basePayload, format: 'svg' };
    const dxfPayload = { ...basePayload, format: 'dxf' };
    
    if (extracted) {
      svgPayload.filename = `${extracted}.svg`;
      dxfPayload.filename = `${extracted}.dxf`;
    }

    const [svgResponse, dxfResponse] = await Promise.all([
      fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(svgPayload),
      }),
      fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dxfPayload),
      }),
    ]);

    const svgResult = await svgResponse.json();
    const dxfResult = await dxfResponse.json();

    if (!svgResponse.ok || svgResult.status !== 'ok') {
      throw new Error(svgResult.message || '無法產生 SVG QR Code');
    }
    if (!dxfResponse.ok || dxfResult.status !== 'ok') {
      throw new Error(dxfResult.message || '無法產生 DXF QR Code');
    }

    setMessage('產生成功！SVG 和 DXF 檔案已準備下載。', 'success');

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

    // 處理 DXF
    const dxfByteString = atob(dxfResult.data);
    const dxfArrayBuffer = new ArrayBuffer(dxfByteString.length);
    const dxfUintArray = new Uint8Array(dxfArrayBuffer);
    for (let i = 0; i < dxfByteString.length; i += 1) {
      dxfUintArray[i] = dxfByteString.charCodeAt(i);
    }
    const dxfBlob = new Blob([dxfArrayBuffer], { type: dxfResult.mime });
    dxfBlobUrl = URL.createObjectURL(dxfBlob);

    const dxfDownloadBase = dxfResult.filename
      ? dxfResult.filename.replace(/\.[^.]+$/, '')
      : extracted ?? 'qrcode';
    els.downloadDxf.href = dxfBlobUrl;
    els.downloadDxf.download = `${dxfDownloadBase}.dxf`;
    els.downloadDxf.classList.remove('disabled');
    els.downloadDxf.textContent = '下載 DXF';

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

checkServer();
setInterval(checkServer, 5000);
