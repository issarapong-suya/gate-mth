/* ═══════════════════════════════════════
   MTH Gate Control – main.js (v3 - Tuya Integrated)
   ═══════════════════════════════════════ */

let gateIsOpen = false;

// ── Tab Navigation ───────────────────────
function showTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  ['control', 'setup', 'info'].forEach(id => {
    const el = document.getElementById(`tab-${id}`);
    if (el) el.style.display = (id === tabId) ? 'block' : 'none';
  });
  // Active button
  const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick')?.includes(tabId));
  if (activeBtn) activeBtn.classList.add('active');
}

function showKeyGuide() {
  const el = document.getElementById('keyGuide');
  if (el) {
    el.style.display = (el.style.display === 'none' || !el.style.display) ? 'block' : 'none';
  }
}

// ── Toast Alerts ────────────────────────
function showToast(message, type = 'success', targetId = 'toast') {
  const toast = document.getElementById(targetId);
  if (!toast) return;
  toast.textContent = message;
  toast.className = `toast ${type}`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.className = 'toast';
    toast.textContent = '';
  }, 6000);
}

// ── Button Loading States ───────────────
function setLoading(active) {
  ['btnOpen', 'btnClose'].forEach(id => {
    const b = document.getElementById(id);
    if (b) {
      b.disabled = active;
      b.classList.toggle('loading', active);
    }
  });
}

// ── Visual Gate State ───────────────────
function setGateState(isOpen) {
  gateIsOpen = isOpen;
  const arm = document.getElementById('gateArm');
  const label = document.getElementById('gateStateLabel');
  if (arm && label) {
    if (isOpen) {
      arm.classList.add('open');
      label.textContent = 'เปิดอยู่';
      label.className = 'gate-state-label state-open';
    } else {
      arm.classList.remove('open');
      label.textContent = 'ปิดอยู่';
      label.className = 'gate-state-label state-close';
    }
  }
}

// ── Gate Actions (Open / Close) ─────────
async function triggerGate(action) {
  const endpoint = action === 'open' ? '/api/open' : '/api/close';
  setLoading(true);

  try {
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const data = await resp.json();

    if (data.success) {
      setGateState(action === 'open');
      showToast(`✅ ${data.message} [${data.timestamp}]`, 'success', 'toast');
    } else {
      showToast(`❌ ${data.message}`, 'error', 'toast');
    }
    setTimeout(loadEvents, 600);
  } catch (err) {
    showToast(`❌ เชื่อมต่อเซิร์ฟเวอร์ไม่ได้: ${err.message}`, 'error', 'toast');
  } finally {
    setLoading(false);
  }
}

// ── Status Polling ──────────────────────
async function pollStatus() {
  try {
    const resp = await fetch('/api/status');
    const data = await resp.json();

    const dot = document.getElementById('statusDot');
    const label = document.getElementById('statusLabel');
    const tuyaBadge = document.getElementById('tuyaBadge');

    if (dot && label) {
      if (data.online) {
        dot.className = 'status-dot online';
        label.textContent = 'Online';
      } else {
        dot.className = 'status-dot offline';
        label.textContent = 'WG Offline';
      }
    }

    if (tuyaBadge) {
      if (data.tuya_ready) {
        tuyaBadge.className = 'tuya-badge ready';
        tuyaBadge.textContent = 'Tuya: Ready ✓';
      } else {
        tuyaBadge.className = 'tuya-badge missing';
        tuyaBadge.textContent = 'Tuya: Not Ready ⚠';
      }
    }

    // Door sensors
    (data.door_sensors || []).forEach((s, i) => {
      const c = document.querySelector(`#sensor${i + 1} .sensor-circle`);
      if (c) c.className = 'sensor-circle ' + (s ? 'on' : 'off');
    });

  } catch {
    const dot = document.getElementById('statusDot');
    const label = document.getElementById('statusLabel');
    if (dot) dot.className = 'status-dot offline';
    if (label) label.textContent = 'Server Offline';
  }
}

// ── Event Log ───────────────────────────
async function loadEvents() {
  try {
    const resp = await fetch('/api/events');
    const events = await resp.json();
    const tbody = document.getElementById('eventBody');
    if (!tbody) return;

    if (!events.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="empty">ยังไม่มีเหตุการณ์</td></tr>';
      return;
    }

    tbody.innerHTML = events.map(e => {
      const isOpen = e.action.includes('เปิด');
      const icon = isOpen ? '🔓' : '🔒';
      return `<tr>
        <td style="white-space:nowrap;color:#8b949e;">${e.time}</td>
        <td>${icon} ${e.action}</td>
        <td><span class="badge ${e.status === 'สำเร็จ' ? 'badge-ok' : 'badge-err'}">${e.status}</span></td>
        <td style="color:#8b949e;font-size:.8rem;">${e.detail}</td>
      </tr>`;
    }).join('');
  } catch {}
}

// ── Tuya Setup Functions ────────────────
function populateForm(ip, devId, version = '3.3') {
  if (ip) document.getElementById('fIp').value = ip;
  if (devId) document.getElementById('fDevId').value = devId;
  if (version) document.getElementById('fVer').value = version;
  showToast(`เลือกอุปกรณ์ IP: ${ip}`, 'success', 'toast2');
}

async function scanDevices() {
  const btn = document.getElementById('btnScan');
  const box = document.getElementById('scanResult');
  btn.disabled = true;
  btn.textContent = '⏳ กำลังสแกน...';
  box.innerHTML = 'กำลังค้นหาอุปกรณ์ Tuya ในวงแลน (ใช้เวลาประมาณ 10-15 วินาที)...';

  try {
    const resp = await fetch('/api/tuya/scan', { method: 'POST' });
    const data = await resp.json();

    if (data.success && data.devices && data.devices.length > 0) {
      box.innerHTML = data.devices.map(d => `
        <div class="device-card">
          <div class="device-info">
            <div class="device-ip">${d.ip}</div>
            <div class="device-id">ID: ${d.device_id}</div>
            <div style="font-size:0.75rem; color:#8b949e;">Ver: ${d.version || '3.3'} | Product: ${d.product || '-'}</div>
          </div>
          <button class="btn-use" onclick="populateForm('${d.ip}', '${d.device_id}', '${d.version || '3.3'}')">
            เลือกใช้อุปกรณ์นี้ ➜
          </button>
        </div>
      `).join('');
    } else {
      box.innerHTML = `
        <div style="color:var(--warn);">ไม่พบอุปกรณ์ใหม่จากการสแกน broadcast แบบอัตโนมัติ</div>
        <div style="margin-top:0.5rem; font-size:0.8rem;">
          อุปกรณ์ที่ตรวจพบก่อนหน้านี้:
          <div class="device-card" style="margin-top:0.4rem;">
            <div class="device-info">
              <div class="device-ip">13.0.0.144</div>
              <div class="device-id">ID: eb50814c990e458a8fdpvo (v3.3)</div>
            </div>
            <button class="btn-use" onclick="populateForm('13.0.0.144', 'eb50814c990e458a8fdpvo', '3.3')">เลือกใช้อุปกรณ์นี้ ➜</button>
          </div>
          <div class="device-card" style="margin-top:0.4rem;">
            <div class="device-info">
              <div class="device-ip">13.0.0.146</div>
              <div class="device-id">ID: eb72e9655bfb697312myle (v3.4)</div>
            </div>
            <button class="btn-use" onclick="populateForm('13.0.0.146', 'eb72e9655bfb697312myle', '3.4')">เลือกใช้อุปกรณ์นี้ ➜</button>
          </div>
        </div>
      `;
    }
  } catch (err) {
    box.innerHTML = `<span style="color:var(--danger);">สแกนผิดพลาด: ${err.message}</span>`;
  } finally {
    btn.disabled = false;
    btn.textContent = '🔍 สแกนเลย';
  }
}

async function loadTuyaConfig() {
  try {
    const resp = await fetch('/api/tuya/config');
    const cfg = await resp.json();
    if (cfg) {
      if (cfg.ip_address) document.getElementById('fIp').value = cfg.ip_address;
      if (cfg.device_id) document.getElementById('fDevId').value = cfg.device_id;
      if (cfg.local_key && cfg.local_key !== '****') document.getElementById('fKey').value = cfg.local_key;
      if (cfg.version) document.getElementById('fVer').value = cfg.version;
      if (cfg.dp_switch) document.getElementById('fDp').value = cfg.dp_switch;
      if (cfg.pulse_sec) document.getElementById('fPulse').value = cfg.pulse_sec;
    }
  } catch {}
}

async function saveConfig() {
  const ip = document.getElementById('fIp').value.trim();
  const devId = document.getElementById('fDevId').value.trim();
  const key = document.getElementById('fKey').value.trim();
  const ver = document.getElementById('fVer').value;
  const dp = parseInt(document.getElementById('fDp').value) || 1;
  const pulse = parseFloat(document.getElementById('fPulse').value) || 0.8;

  if (!ip || !devId) {
    showToast('กรุณากรอก IP Address และ Device ID', 'error', 'toast2');
    return;
  }

  try {
    const resp = await fetch('/api/tuya/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ip_address: ip,
        device_id: devId,
        local_key: key,
        version: ver,
        dp_switch: dp,
        pulse_sec: pulse
      })
    });
    const data = await resp.json();
    if (data.success) {
      showToast('✅ บันทึกการตั้งค่า Tuya สำเร็จแล้ว', 'success', 'toast2');
      pollStatus();
    } else {
      showToast(`❌ ${data.message}`, 'error', 'toast2');
    }
  } catch (err) {
    showToast(`❌ เกิดข้อผิดพลาด: ${err.message}`, 'error', 'toast2');
  }
}

async function testRelay() {
  const toastId = 'toast2';
  showToast('กำลังส่งสัญญาณ Pulse ทดสอบไปยัง Tuya relay...', 'warn', toastId);
  try {
    const resp = await fetch('/api/tuya/test', { method: 'POST' });
    const data = await resp.json();
    if (data.success) {
      showToast(`✅ ${data.message}`, 'success', toastId);
    } else {
      showToast(`❌ ${data.message}`, 'error', toastId);
    }
  } catch (err) {
    showToast(`❌ เกิดข้อผิดพลาด: ${err.message}`, 'error', toastId);
  }
}

// ── Initialize ──────────────────────────
setGateState(false);
loadTuyaConfig();
pollStatus();
loadEvents();
setInterval(pollStatus, 8000);
setInterval(loadEvents, 15000);
