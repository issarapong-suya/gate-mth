/* ════════════════════════════════════════════════════════════════
   MTH GATE – mobile.js (v5 Power Icon & Safe Toast Edition)
   Theme Switcher | Power Icon Anim | Safe Position Toast | Logout Modal
   ════════════════════════════════════════════════════════════════ */

let currentPin = '';
let currentUserToken = null;
let currentUserName = '';
let isOpening = false;
let toastTimeout = null;

// ── Haptic Vibration ─────────────────────
function triggerHaptic(pattern = 40) {
  if ('vibrate' in navigator) {
    try { navigator.vibrate(pattern); } catch (_) {}
  }
}

// ── Automatic Time-Based Theme (06:00-17:59 Light, 18:00-05:59 Dark) ──
function getTimeBasedTheme() {
  const hour = new Date().getHours();
  return (hour >= 6 && hour < 18) ? 'light' : 'dark';
}

function initTheme() {
  const manual = localStorage.getItem('mth_theme_manual');
  const theme = manual || getTimeBasedTheme();
  setTheme(theme, false);

  // ตรวจสอบเวลาทุกๆ 1 นาที หากไม่ได้ล็อคโหมดเอง ให้ปรับตามเวลาอัตโนมัติ
  setInterval(() => {
    if (!localStorage.getItem('mth_theme_manual')) {
      const autoTheme = getTimeBasedTheme();
      if (document.documentElement.getAttribute('data-theme') !== autoTheme) {
        setTheme(autoTheme, false);
      }
    }
  }, 60000);
}

function setTheme(theme, isManual = true) {
  document.documentElement.setAttribute('data-theme', theme);
  if (isManual) {
    localStorage.setItem('mth_theme_manual', theme);
  }
  
  // Update Meta Theme Color
  const metaTheme = document.querySelector('meta[name="theme-color"]');
  if (metaTheme) {
    metaTheme.setAttribute('content', theme === 'dark' ? '#0a0e17' : '#f8fafc');
  }
}

function toggleTheme() {
  triggerHaptic(25);
  const current = document.documentElement.getAttribute('data-theme') || getTimeBasedTheme();
  const next = current === 'dark' ? 'light' : 'dark';
  setTheme(next, true);
  showSafeToast(`สลับเป็น ${next === 'dark' ? 'โหมดมืด 🌙' : 'โหมดสว่าง ☀️'}`, 'success');
}

// ── Safe Position Toast (วางใต้ User Chip ไม่บัง Header หรือชื่อ) ──
function showSafeToast(message, type = 'success') {
  const slot = document.getElementById('toastSlot');
  if (!slot) return;

  clearTimeout(toastTimeout);

  const iconSvg = type === 'success'
    ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`
    : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;

  slot.innerHTML = `
    <div class="luxury-toast-pill ${type}">
      ${iconSvg}
      <span>${message}</span>
    </div>
  `;

  toastTimeout = setTimeout(() => {
    const pill = slot.querySelector('.luxury-toast-pill');
    if (pill) {
      pill.style.opacity = '0';
      pill.style.transform = 'translateY(-5px) scale(0.95)';
      pill.style.transition = 'all 0.25s ease';
      setTimeout(() => { slot.innerHTML = ''; }, 260);
    }
  }, 3500);
}

// ── Token & Auth Management ──────────────
function saveAuth(user) {
  if (!user || !user.token) return;
  currentUserToken = user.token;
  currentUserName = user.name;
  localStorage.setItem('mth_gate_token', user.token);
  localStorage.setItem('mth_gate_user', JSON.stringify(user));
  showScreen('gate');
  renderUser(user);
}

function clearAuth() {
  currentUserToken = null;
  currentUserName = '';
  localStorage.removeItem('mth_gate_token');
  localStorage.removeItem('mth_gate_user');
  currentPin = '';
  updatePinDots();
  showScreen('login');
}

function showScreen(screenName) {
  document.getElementById('screen-login').style.display = (screenName === 'login') ? 'flex' : 'none';
  document.getElementById('screen-gate').style.display = (screenName === 'gate') ? 'flex' : 'none';
}

function renderUser(user) {
  const nameEl = document.getElementById('userName');
  if (nameEl) nameEl.textContent = user.name || 'เจ้าหน้าที่';
}

// ── Keypad PIN System (6 Digits) ──────────
function pressKey(num) {
  triggerHaptic(30);
  if (currentPin.length < 6) {
    currentPin += num;
    updatePinDots();
    if (currentPin.length === 6) {
      setTimeout(verifyPin, 160);
    }
  }
}

function deletePin() {
  triggerHaptic(20);
  if (currentPin.length > 0) {
    currentPin = currentPin.slice(0, -1);
    updatePinDots();
  }
}

function clearPin() {
  triggerHaptic(20);
  currentPin = '';
  updatePinDots();
  const errEl = document.getElementById('pinError');
  if (errEl) errEl.textContent = '';
}

function updatePinDots() {
  const dots = document.querySelectorAll('#pinDots .pin-digit');
  dots.forEach((dot, idx) => {
    dot.classList.toggle('active', idx < currentPin.length);
  });
}

async function verifyPin() {
  const errEl = document.getElementById('pinError');
  if (errEl) errEl.textContent = 'กำลังตรวจสอบ...';

  const boundToken = localStorage.getItem('mth_gate_token');

  try {
    const resp = await fetch('/api/verify_pin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pin: currentPin, bound_token: boundToken })
    });
    const data = await resp.json();

    if (data.success && data.user) {
      if (errEl) errEl.textContent = '';
      saveAuth(data.user);
      showSafeToast(data.message || `ยินดีต้อนรับ ${data.user.name}`, 'success');
    } else {
      triggerHaptic(180);
      if (errEl) errEl.textContent = data.message || 'รหัส PIN ไม่ถูกต้อง';
      currentPin = '';
      updatePinDots();
    }
  } catch (err) {
    if (errEl) errEl.textContent = 'ไม่สามารถเชื่อมต่อระบบได้';
    currentPin = '';
    updatePinDots();
  }
}

// ── Power Button Gate Opener ─────────────
async function doOpenGate() {
  if (isOpening) return;
  isOpening = true;

  const btn = document.getElementById('btnGateOpen');
  const hintLabel = document.getElementById('gateActionHint');

  // Activate glowing opening state on the power button
  triggerHaptic(60);
  btn.classList.add('opening');
  if (hintLabel) hintLabel.textContent = 'กำลังส่งคำสั่งเปิดไม้กั้น...';

  try {
    const resp = await fetch('/api/open', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: currentUserToken })
    });
    const data = await resp.json();

    if (data.success) {
      triggerHaptic([70, 50, 90]); // Success double vibration
      if (hintLabel) hintLabel.textContent = 'ไม้กั้นกำลังยกขึ้น เรียบร้อย ✓';
      showSafeToast('ส่งสัญญาณเปิดไม้กั้นสำเร็จ', 'success');

      // ส่งสัญญาณแจ้งเตือนให้หน้าต่างแอดมินรีเฟรชประวัติทันที
      try {
        localStorage.setItem('mth_gate_event_trigger', Date.now().toString());
        if (typeof BroadcastChannel !== 'undefined') {
          const bc = new BroadcastChannel('mth_gate_channel');
          bc.postMessage({ type: 'GATE_OPENED', user: data.user_name, time: data.timestamp });
          bc.close();
        }
      } catch (_) {}
    } else {
      triggerHaptic(200);
      if (hintLabel) hintLabel.textContent = data.message || 'ไม่สามารถเปิดได้';
      showSafeToast(data.message || 'เปิดไม้กั้นไม่สำเร็จ', 'error');
      
      if (resp.status === 401 || resp.status === 403) {
        setTimeout(clearAuth, 2200);
      }
    }
  } catch (err) {
    triggerHaptic(200);
    if (hintLabel) hintLabel.textContent = 'ไม่สามารถติดต่อเซิร์ฟเวอร์';
    showSafeToast(`เชื่อมต่อไม่ได้: ${err.message}`, 'error');
  } finally {
    // Revert back to ready state after 3 seconds
    setTimeout(() => {
      btn.classList.remove('opening');
      if (hintLabel) hintLabel.textContent = 'แตะปุ่มเพื่อส่งสัญญาณเปิดไม้กั้น';
      isOpening = false;
    }, 3000);
  }
}

// ── Custom Logout Modal ──────────────────
function openLogoutModal() {
  triggerHaptic(30);
  const modal = document.getElementById('logoutModal');
  if (modal) modal.style.display = 'flex';
}

function closeLogoutModal(e) {
  if (!e || e.target.id === 'logoutModal' || e.target.classList.contains('btn-modal-cancel')) {
    const modal = document.getElementById('logoutModal');
    if (modal) modal.style.display = 'none';
  }
}

async function confirmLogout() {
  triggerHaptic(40);
  const modal = document.getElementById('logoutModal');
  if (modal) modal.style.display = 'none';

  try {
    await fetch('/api/logout', { method: 'POST' });
  } catch (_) {}
  clearAuth();
  showSafeToast('ออกจากระบบเรียบร้อยแล้ว', 'success');
}

// ── Connection Status Poller ─────────────
async function pollStatus() {
  try {
    const resp = await fetch('/api/status');
    const data = await resp.json();
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');

    if (data.online) {
      if (dot) dot.className = 'status-dot online';
      if (text) text.textContent = 'ออนไลน์';
    } else {
      if (dot) dot.className = 'status-dot offline';
      if (text) text.textContent = 'ออฟไลน์';
    }
  } catch (_) {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    if (dot) dot.className = 'status-dot offline';
    if (text) text.textContent = 'ขัดข้อง';
  }
}

// ── Application Initialization ───────────
(function init() {
  // 1. Initialize Theme (Dark/Light)
  initTheme();

  // 2. Direct access via URL token (e.g. from LINE or QR Code)
  if (window.SERVER_USER) {
    saveAuth(window.SERVER_USER);
    if (window.history.replaceState) {
      window.history.replaceState({}, document.title, '/');
    }
    showSafeToast(`ยินดีต้อนรับ ${window.SERVER_USER.name}`, 'success');
    pollStatus();
    setInterval(pollStatus, 8000);
    return;
  }

  // 3. Persistent session on this device
  const savedToken = localStorage.getItem('mth_gate_token');
  const savedUserJson = localStorage.getItem('mth_gate_user');
  if (savedToken && savedUserJson) {
    try {
      const user = JSON.parse(savedUserJson);
      currentUserToken = savedToken;
      currentUserName = user.name;
      showScreen('gate');
      renderUser(user);
      pollStatus();
      setInterval(pollStatus, 8000);
      return;
    } catch (_) {}
  }

  // 4. Default: Show PIN Prompt
  showScreen('login');
  pollStatus();
  setInterval(pollStatus, 8000);
})();
