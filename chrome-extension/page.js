const API_BASE_URL = 'https://api.qrcode-monkey.com';

const urlInput = document.getElementById('url-input');
const sizeInput = document.getElementById('size-input');
const generateBtn = document.getElementById('generate-btn');
const downloadPngBtn = document.getElementById('download-png-btn');
const downloadSvgBtn = document.getElementById('download-svg-btn');
const downloadEpsBtn = document.getElementById('download-eps-btn');
const previewImage = document.getElementById('preview-image');
const previewPlaceholder = document.getElementById('preview-placeholder');
const loadingLayer = document.getElementById('loading');
const errorMessage = document.getElementById('error-message');
const logoInput = document.getElementById('logo-input');
const logoStatus = document.getElementById('logo-status');
const clearLogoBtn = document.getElementById('clear-logo-btn');

const FIXED_CONFIG = {
    body: 'diamond',
    eye: 'frame12',
    eyeBall: 'ball14',
    bodyColor: '#000000',
    bgColor: '#ffffff',
    eye1Color: '#000000',
    eye2Color: '#000000',
    eye3Color: '#000000',
    eyeBall1Color: '#000000',
    eyeBall2Color: '#000000',
    eyeBall3Color: '#000000'
};

let currentBlob = null;
let currentObjectUrl = null;
let logoToken = null;
let lastPayload = null;
let activeLogoRequestId = 0;

generateBtn.addEventListener('click', generateQrCode);
downloadPngBtn.addEventListener('click', () => downloadFormat('png'));
downloadSvgBtn.addEventListener('click', () => downloadFormat('svg'));
downloadEpsBtn.addEventListener('click', () => downloadFormat('eps'));
logoInput.addEventListener('change', handleLogoChange);
clearLogoBtn.addEventListener('click', () => {
    logoToken = null;
    logoInput.value = '';
    logoStatus.textContent = '尚未上傳 Logo';
    clearLogoBtn.disabled = true;
    lastPayload = null;
});

enablePersistedSettings();
resetState();

function enablePersistedSettings() {
    chrome.storage.sync.get(['qrUrl', 'qrSize'], (items) => {
        if (items.qrUrl) urlInput.value = items.qrUrl;
        if (items.qrSize) sizeInput.value = items.qrSize;
    });

    [urlInput, sizeInput].forEach((element) => {
        element.addEventListener('change', () => {
            chrome.storage.sync.set({
                qrUrl: urlInput.value,
                qrSize: sizeInput.value
            });
        });
    });
}

function resetState() {
    logoToken = null;
    logoInput.value = '';
    logoStatus.textContent = '尚未上傳 Logo';
    clearLogoBtn.disabled = true;
    clearPreview();
    showError('');
    showLoading(false);
}

function showLoading(show) {
    loadingLayer.classList.toggle('hidden', !show);
    generateBtn.disabled = show;
}

function showError(message) {
    if (!message) {
        errorMessage.classList.add('hidden');
        errorMessage.textContent = '';
        return;
    }
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
}

function clearPreview() {
    if (currentObjectUrl) {
        URL.revokeObjectURL(currentObjectUrl);
        currentObjectUrl = null;
    }
    currentBlob = null;
    previewImage.style.display = 'none';
    previewImage.src = '';
    previewPlaceholder.textContent = 'QR 碼預覽將顯示在這裡';
    setDownloadButtons(false);
}

function setDownloadButtons(enabled) {
    downloadPngBtn.disabled = !enabled;
    downloadSvgBtn.disabled = !enabled;
    downloadEpsBtn.disabled = !enabled;
}

async function handleLogoChange(event) {
    if (!event.target.files || !event.target.files[0]) {
        return;
    }

    const file = event.target.files[0];
    logoStatus.textContent = `上傳中：${file.name}`;
    clearLogoBtn.disabled = true;
    const requestId = ++activeLogoRequestId;

    try {
        const token = await uploadLogoFile(file);
        if (requestId !== activeLogoRequestId) {
            return;
        }
        logoToken = token;
        logoStatus.textContent = `已上傳：${file.name}`;
        clearLogoBtn.disabled = false;
        showError('');
    } catch (error) {
        console.error('Logo 上傳失敗:', error);
        if (requestId !== activeLogoRequestId) {
            return;
        }
        logoToken = null;
        logoStatus.textContent = '上傳失敗，請重新選擇';
        clearLogoBtn.disabled = true;
        logoInput.value = '';
        showError(`Logo 上傳失敗：${error.message}`);
    }
}

async function uploadLogoFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/qr/uploadImage`, {
        method: 'POST',
        body: formData
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `HTTP ${response.status}`);
    }

    const result = await response.json();
    if (!result.file) {
        throw new Error('回應格式錯誤');
    }
    return result.file;
}

async function generateQrCode() {
    const data = urlInput.value.trim();
    if (!data) {
        showError('請輸入網址或文字');
        return;
    }

    const size = Math.min(Math.max(parseInt(sizeInput.value, 10) || 300, 100), 1000);

    showError('');
    clearPreview();
    showLoading(true);

    const config = { ...FIXED_CONFIG };
    if (logoToken) {
        config.logo = logoToken;
        config.logoMode = 'default';
    }

    lastPayload = { data, size, config: { ...config } };

    const requestPayload = {
        data,
        size,
        config,
        file: 'png',
        download: false
    };

    try {
        console.log('發送 API 請求 (PNG):', requestPayload);
        const response = await fetch(`${API_BASE_URL}/qr/custom`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestPayload)
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(`API 錯誤 (${response.status}): ${text}`);
        }

        const blob = await response.blob();
        if (!blob || blob.size === 0) {
            throw new Error('API 返回空數據');
        }

        currentBlob = blob;
        currentObjectUrl = URL.createObjectURL(blob);

        previewImage.src = currentObjectUrl;
        previewImage.style.display = 'block';
        previewPlaceholder.textContent = '';
        setDownloadButtons(true);
        console.log('QR 碼產生成功');
    } catch (error) {
        console.error('產生 QR 碼失敗:', error);
        showError(`產生 QR 碼失敗：${error.message}`);
        lastPayload = null;
    } finally {
        showLoading(false);
    }
}

async function downloadFormat(format) {
    if (!lastPayload) {
        showError('請先產生 QR 碼後再下載');
        return;
    }

    if (format === 'png' && currentBlob) {
        const url = currentObjectUrl || URL.createObjectURL(currentBlob);
        triggerDownload(url, 'qrcode.png');
        if (!currentObjectUrl) {
            URL.revokeObjectURL(url);
        }
        return;
    }

    showLoading(true);
    try {
        const payload = {
            ...lastPayload,
            file: format,
            download: false
        };
        console.log(`發送 API 請求 (${format.toUpperCase()}):`, payload);
        const response = await fetch(`${API_BASE_URL}/qr/custom`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(`API 錯誤 (${response.status}): ${text}`);
        }

        const blob = await response.blob();
        if (!blob || blob.size === 0) {
            throw new Error('API 返回空數據');
        }

        const url = URL.createObjectURL(blob);
        triggerDownload(url, `qrcode.${format}`);
        URL.revokeObjectURL(url);
    } catch (error) {
        console.error(`下載 ${format.toUpperCase()} 失敗:`, error);
        showError(`下載 ${format.toUpperCase()} 失敗：${error.message}`);
    } finally {
        showLoading(false);
    }
}

function triggerDownload(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

clearPreview();
showError('');
showLoading(false);
