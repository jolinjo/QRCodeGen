const API_BASE_URL = 'https://api.qrcode-monkey.com';

const urlInput = document.getElementById('url-input');
const sizeInput = document.getElementById('size-input');
const formatSelect = document.getElementById('format-select');
const generateBtn = document.getElementById('generate-btn');
const downloadBtn = document.getElementById('download-btn');
const previewImage = document.getElementById('preview-image');
const previewPlaceholder = document.getElementById('preview-placeholder');
const loadingLayer = document.getElementById('loading');
const errorMessage = document.getElementById('error-message');

let currentBlob = null;
let currentObjectUrl = null;

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

generateBtn.addEventListener('click', generateQrCode);
downloadBtn.addEventListener('click', downloadQrCode);

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
    downloadBtn.disabled = true;
}

async function generateQrCode() {
    const data = urlInput.value.trim();
    if (!data) {
        showError('請輸入網址或文字');
        return;
    }

    const size = Math.min(Math.max(parseInt(sizeInput.value, 10) || 300, 100), 1000);
    const fileFormat = formatSelect.value;

    showError('');
    clearPreview();
    showLoading(true);

    const config = { ...FIXED_CONFIG };

    const payload = {
        data,
        size,
        config,
        file: fileFormat,
        download: false
    };

    try {
        console.log('發送 API 請求:', payload);
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

        currentBlob = blob;
        currentObjectUrl = URL.createObjectURL(blob);

        if (fileFormat === 'png') {
            previewImage.src = currentObjectUrl;
            previewImage.style.display = 'block';
            previewPlaceholder.textContent = '';
        } else {
            previewImage.style.display = 'none';
            previewPlaceholder.textContent = `QR 碼已產生 (${fileFormat.toUpperCase()} 格式)`;
        }

        downloadBtn.disabled = false;
        console.log('QR 碼產生成功');
    } catch (error) {
        console.error('產生 QR 碼失敗:', error);
        showError(`產生 QR 碼失敗：${error.message}`);
    } finally {
        showLoading(false);
    }
}

function downloadQrCode() {
    if (!currentBlob) {
        showError('沒有可下載的 QR 碼');
        return;
    }

    const format = formatSelect.value;
    const filename = `qrcode.${format}`;
    const url = currentObjectUrl || URL.createObjectURL(currentBlob);

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    if (!currentObjectUrl) {
        URL.revokeObjectURL(url);
    }
}

// 初始清理
clearPreview();
showError('');
showLoading(false);
