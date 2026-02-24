/**
 * embed.js — Data Embedding Page Logic
 * Handles: tab switching, file upload/drag-drop, text input,
 *          preview, and calling the /api/embed endpoint.
 */

// =============================================
//  THEME (shared with main page)
// =============================================
(function initTheme() {
    const saved = localStorage.getItem('derma-theme');
    if (saved) document.documentElement.setAttribute('data-theme', saved);
    updateThemeIcon();
})();

function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'light' ? 'dark' : 'light';
    if (next === 'dark') {
        html.removeAttribute('data-theme');
        localStorage.removeItem('derma-theme');
    } else {
        html.setAttribute('data-theme', 'light');
        localStorage.setItem('derma-theme', 'light');
    }
    updateThemeIcon();
}

function updateThemeIcon() {
    const btn = document.getElementById('theme-btn');
    if (!btn) return;
    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    btn.querySelector('i').className = isLight ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
}

// =============================================
//  STATE
// =============================================
let activeTab = 'file';   // 'file' | 'text'
let selectedFile = null;  // File object

// =============================================
//  TAB SWITCHING
// =============================================
function switchTab(tab) {
    activeTab = tab;

    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    document.getElementById('tab-' + tab).classList.add('active');
    document.getElementById('content-' + tab).classList.add('active');

    // Reset preview when switching
    resetPreviewPlaceholder();
}

// =============================================
//  FILE HANDLING
// =============================================
function handleDragOver(e) {
    e.preventDefault();
    document.getElementById('dropzone').classList.add('dragover');
}

function handleDragLeave(e) {
    document.getElementById('dropzone').classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    document.getElementById('dropzone').classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) applyFile(file);
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) applyFile(file);
}

function applyFile(file) {
    const allowed = ['text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    const ext = file.name.split('.').pop().toLowerCase();

    if (!['txt', 'docx'].includes(ext)) {
        addLog('ชนิดไฟล์ไม่รองรับ — กรุณาเลือก .txt หรือ .docx', 'error');
        return;
    }

    selectedFile = file;

    // Show file card
    const card = document.getElementById('file-card');
    card.style.display = 'flex';

    const iconEl = document.getElementById('file-card-icon');
    iconEl.className = 'file-card-icon ' + ext;
    iconEl.innerHTML = ext === 'txt'
        ? '<i class="fa-solid fa-file-lines"></i>'
        : '<i class="fa-solid fa-file-word"></i>';

    document.getElementById('file-card-name').textContent = file.name;
    document.getElementById('file-card-size').textContent = formatBytes(file.size);

    // Read and show preview (txt only)
    if (ext === 'txt') {
        const reader = new FileReader();
        reader.onload = (ev) => renderPreview(ev.target.result, file.name);
        reader.readAsText(file, 'UTF-8');
    } else {
        renderPreview(`[ไฟล์ Word: ${file.name}]\n\nไม่สามารถแสดง Preview ของไฟล์ .docx ได้\nระบบจะแปลงและ Embed เนื้อหาอัตโนมัติเมื่อกด "เริ่ม Embedding"`, file.name);
    }

    addLog(`เลือกไฟล์: ${file.name} (${formatBytes(file.size)})`, 'info');
}

function removeFile() {
    selectedFile = null;
    document.getElementById('file-card').style.display = 'none';
    document.getElementById('file-input').value = '';
    resetPreviewPlaceholder();
    addLog('ลบไฟล์ออกแล้ว', 'warn');
}

// =============================================
//  TEXT INPUT
// =============================================
function updateTextPreview() {
    const txt = document.getElementById('text-input').value;
    const charCount = txt.length;
    const wordCount = txt.trim() ? txt.trim().split(/\s+/).length : 0;

    document.getElementById('char-count').textContent = charCount.toLocaleString() + ' ตัวอักษร';
    document.getElementById('word-count').textContent = wordCount.toLocaleString() + ' คำ';

    if (txt.trim()) {
        renderPreview(txt, 'ข้อความ (Direct Input)');
    } else {
        resetPreviewPlaceholder();
    }
}

// =============================================
//  PREVIEW
// =============================================
function renderPreview(content, sourceName) {
    const box = document.getElementById('preview-box');
    const maxChars = 3000;
    const truncated = content.length > maxChars;
    const display = truncated
        ? content.slice(0, maxChars) + `\n\n... [แสดงเพียง ${maxChars.toLocaleString()} ตัวอักษรแรก จากทั้งหมด ${content.length.toLocaleString()} ตัวอักษร]`
        : content;

    box.innerHTML = `
        <div style="margin-bottom:8px; padding-bottom:8px; border-bottom:1px solid var(--border-glass); font-size:11px; color:var(--text-secondary); display:flex; align-items:center; gap:6px;">
            <i class="fa-solid fa-file-circle-check" style="color:var(--primary)"></i>
            <strong>${escapeHtml(sourceName)}</strong>
            <span style="margin-left:auto">${content.length.toLocaleString()} ตัวอักษร</span>
        </div>
        <div style="white-space:pre-wrap; word-wrap:break-word;">${escapeHtml(display)}</div>
    `;
}

function resetPreviewPlaceholder() {
    document.getElementById('preview-box').innerHTML = `
        <div class="preview-placeholder">
            <i class="fa-solid fa-file-magnifying-glass"></i>
            <p>เนื้อหาของไฟล์หรือข้อความที่คุณเลือกจะแสดงที่นี่</p>
        </div>`;
}

function clearPreview() {
    resetPreviewPlaceholder();
    if (activeTab === 'file') {
        removeFile();
    } else {
        document.getElementById('text-input').value = '';
        updateTextPreview();
    }
    resetStats();
}

// =============================================
//  EMBEDDING
// =============================================
async function startEmbedding() {
    const chunkSize    = parseInt(document.getElementById('chunk-size').value)   || 500;
    const chunkOverlap = parseInt(document.getElementById('chunk-overlap').value) || 50;

    // Validate
    if (activeTab === 'file' && !selectedFile) {
        addLog('กรุณาเลือกไฟล์ก่อนกด Embed', 'error');
        shakeButton();
        return;
    }
    if (activeTab === 'text' && !document.getElementById('text-input').value.trim()) {
        addLog('กรุณาพิมพ์ข้อความก่อนกด Embed', 'error');
        shakeButton();
        return;
    }

    setLoadingState(true);
    setStatusIndicator('working', 'กำลังประมวลผล...');
    addLog('เริ่มกระบวนการ Embedding...', 'process');

    try {
        let response;

        if (activeTab === 'file') {
            addLog(`กำลังอ่านไฟล์ "${selectedFile.name}"...`, 'process');
            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('chunk_size', chunkSize);
            formData.append('chunk_overlap', chunkOverlap);

            response = await fetch('/api/embed', {
                method: 'POST',
                body: formData
            });
        } else {
            const text = document.getElementById('text-input').value.trim();
            addLog(`กำลังส่งข้อความ (${text.length.toLocaleString()} ตัวอักษร)...`, 'process');

            response = await fetch('/api/embed', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    chunk_size: chunkSize,
                    chunk_overlap: chunkOverlap
                })
            });
        }

        const data = await response.json();

        if (!response.ok || data.error) {
            throw new Error(data.error || `Server error: ${response.status}`);
        }

        // Success
        addLog(`✓ Embedding สำเร็จ! เพิ่ม ${data.chunks_added} chunks เข้าฐานข้อมูล`, 'success');
        addLog(`✓ ข้อมูลพร้อมใช้งานใน DermaAI Chat แล้ว`, 'success');
        setStatusIndicator('success', 'สำเร็จ');
        updateStats(data.chunks_added, data.total_chars, 'สำเร็จ');
        showSuccessFlash();

    } catch (err) {
        console.error('Embed error:', err);
        addLog(`✗ เกิดข้อผิดพลาด: ${err.message}`, 'error');
        setStatusIndicator('error', 'ผิดพลาด');
        updateStats('—', '—', 'ผิดพลาด', true);
    } finally {
        setLoadingState(false);
    }
}

// =============================================
//  UI HELPERS
// =============================================
function setLoadingState(loading) {
    const btn = document.getElementById('embed-btn');
    if (loading) {
        btn.disabled = true;
        btn.classList.add('loading');
        btn.innerHTML = `
            <div class="spinner"></div>
            <span>กำลัง Embedding...</span>
        `;
    } else {
        btn.disabled = false;
        btn.classList.remove('loading');
        btn.innerHTML = `<i class="fa-solid fa-bolt"></i><span>เริ่ม Embedding</span>`;
    }
}

function setStatusIndicator(type, text) {
    const dot  = document.querySelector('.status-dot');
    const span = document.getElementById('status-text');
    dot.className = 'status-dot ' + type;
    span.textContent = text;
}

function addLog(message, type = 'info') {
    const log = document.getElementById('status-log');
    const now = new Date();
    const time = now.toTimeString().slice(0, 8);

    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `<span class="log-time">${time}</span><span>${escapeHtml(message)}</span>`;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
}

function updateStats(chunks, chars, statusText, isError = false) {
    document.getElementById('val-chunks').textContent = typeof chunks === 'number' ? chunks.toLocaleString() : chunks;
    document.getElementById('val-chars').textContent  = typeof chars === 'number' ? chars.toLocaleString() : chars;
    document.getElementById('val-status').textContent = statusText;

    const statStatusCard = document.getElementById('stat-status');
    const icon = statStatusCard.querySelector('.stat-icon');
    if (isError) {
        icon.className = 'stat-icon error-icon';
        icon.innerHTML = '<i class="fa-solid fa-circle-xmark"></i>';
    } else if (statusText === 'สำเร็จ') {
        icon.className = 'stat-icon success';
        icon.innerHTML = '<i class="fa-solid fa-check-circle"></i>';
    }

    document.querySelectorAll('.stat-card').forEach(c => c.classList.add('highlight'));
    setTimeout(() => {
        document.querySelectorAll('.stat-card').forEach(c => c.classList.remove('highlight'));
    }, 2000);
}

function resetStats() {
    document.getElementById('val-chunks').textContent = '—';
    document.getElementById('val-chars').textContent  = '—';
    document.getElementById('val-status').textContent = '—';
    setStatusIndicator('idle', 'พร้อมใช้งาน');
}

function shakeButton() {
    const btn = document.getElementById('embed-btn');
    btn.style.animation = 'shake 0.4s ease';
    btn.addEventListener('animationend', () => { btn.style.animation = ''; }, { once: true });
}

function showSuccessFlash() {
    const flash = document.createElement('div');
    flash.style.cssText = `
        position: fixed; top: 24px; right: 24px; z-index: 9999;
        background: linear-gradient(135deg, #10b981, #059669);
        color: white; padding: 14px 22px;
        border-radius: 12px; font-family: 'Prompt','Inter',sans-serif;
        font-size: 14px; font-weight: 500;
        box-shadow: 0 8px 30px rgba(16,185,129,0.4);
        display: flex; align-items: center; gap: 10px;
        animation: slideInRight 0.4s cubic-bezier(0.16,1,0.3,1) forwards;
    `;
    flash.innerHTML = '<i class="fa-solid fa-circle-check"></i> Embedding สำเร็จแล้ว!';
    document.body.appendChild(flash);
    setTimeout(() => {
        flash.style.opacity = '0';
        flash.style.transform = 'translateX(20px)';
        flash.style.transition = 'all 0.3s ease';
        setTimeout(() => flash.remove(), 300);
    }, 3000);
}

// =============================================
//  UTILITIES
// =============================================
function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// Shake keyframe injection
const shakeStyle = document.createElement('style');
shakeStyle.textContent = `
  @keyframes shake {
    0%,100% { transform: translateX(0); }
    20%      { transform: translateX(-6px); }
    40%      { transform: translateX(6px); }
    60%      { transform: translateX(-4px); }
    80%      { transform: translateX(4px); }
  }
  @keyframes slideInRight {
    from { opacity:0; transform: translateX(30px); }
    to   { opacity:1; transform: translateX(0); }
  }
`;
document.head.appendChild(shakeStyle);
