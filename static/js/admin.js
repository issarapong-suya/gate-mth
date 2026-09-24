/* ════════════════════════════════════════════════════════════════
   MTH GATE – admin.js (v6 Search & Pagination Edition)
   Modern SVG | Real-time Search | Pagination | Modals
   ════════════════════════════════════════════════════════════════ */

// ── State Management ─────────────────────
let rawStaffList = [];
let staffSearchKeyword = '';
let staffCurrentPage = 1;
let staffPageSize = 10;

let rawLogList = [];
let logSearchKeyword = '';
let logCurrentPage = 1;
let logPageSize = 10;

// ── Automatic Time-Based Theme (06:00-17:59 Light, 18:00-05:59 Dark) ──
function getTimeBasedTheme() {
  const hour = new Date().getHours();
  return (hour >= 6 && hour < 18) ? 'light' : 'dark';
}

function initAdminTheme() {
  const manual = localStorage.getItem('mth_theme_manual');
  const theme = manual || getTimeBasedTheme();
  setAdminTheme(theme, false);

  // ตรวจสอบเวลาทุกๆ 1 นาที หากไม่ได้ล็อคโหมดเอง ให้ปรับตามเวลาอัตโนมัติ
  setInterval(() => {
    if (!localStorage.getItem('mth_theme_manual')) {
      const autoTheme = getTimeBasedTheme();
      if (document.documentElement.getAttribute('data-theme') !== autoTheme) {
        setAdminTheme(autoTheme, false);
      }
    }
  }, 60000);
}

function setAdminTheme(theme, isManual = true) {
  document.documentElement.setAttribute('data-theme', theme);
  if (isManual) {
    localStorage.setItem('mth_theme_manual', theme);
  }
}

function toggleAdminTheme() {
  const current = document.documentElement.getAttribute('data-theme') || getTimeBasedTheme();
  const next = current === 'dark' ? 'light' : 'dark';
  setAdminTheme(next, true);
  showAdminToast(`สลับเป็น ${next === 'dark' ? 'โหมดมืด 🌙' : 'โหมดสว่าง ☀️'}`, 'success');
}

// ── Admin Toast ──────────────────────────
function showAdminToast(msg, type = 'success') {
  const container = document.getElementById('adminToastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `admin-toast-pill ${type}`;
  toast.textContent = msg;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.25s ease';
    setTimeout(() => toast.remove(), 260);
  }, 3200);
}

// ── Admin Authentication ─────────────────
async function adminLogin() {
  const pwd = document.getElementById('adminPassword').value.trim();
  const err = document.getElementById('loginError');
  err.textContent = '';

  if (!pwd) {
    err.textContent = 'กรุณาระบุรหัสผ่าน';
    return;
  }

  try {
    const resp = await fetch('/api/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pwd })
    });
    const data = await resp.json();

    if (data.success) {
      document.getElementById('adminPassword').value = '';
      showAdminView(true);
      loadStaffList();
      loadAuditLogs();
      showAdminToast('เข้าสู่ระบบสำเร็จ', 'success');
    } else {
      err.textContent = data.message || 'รหัสผ่านไม่ถูกต้อง';
    }
  } catch (e) {
    err.textContent = 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้';
  }
}

async function adminLogout() {
  await fetch('/api/admin/logout', { method: 'POST' });
  showAdminView(false);
  showAdminToast('ออกจากระบบแล้ว', 'success');
}

let adminSyncInterval = null;

function startAdminSync() {
  if (adminSyncInterval) clearInterval(adminSyncInterval);
  // Real-time fast polling every 2.2 seconds to catch gate opening instantly
  adminSyncInterval = setInterval(() => {
    loadAuditLogs();
  }, 2200);
}

function stopAdminSync() {
  if (adminSyncInterval) {
    clearInterval(adminSyncInterval);
    adminSyncInterval = null;
  }
}

function showAdminView(isLogged) {
  document.getElementById('adminLoginCard').style.display = isLogged ? 'none' : 'block';
  document.getElementById('adminDashboard').style.display = isLogged ? 'block' : 'none';
  document.getElementById('btnAdminLogout').style.display = isLogged ? 'inline-flex' : 'none';

  if (isLogged) {
    loadStaffList();
    loadAuditLogs();
    startAdminSync();
  } else {
    stopAdminSync();
  }
}

// ═════════════════════════════════════════
// 1. STAFF MANAGEMENT (SEARCH & PAGINATION)
// ═════════════════════════════════════════
async function loadStaffList() {
  try {
    const resp = await fetch('/api/admin/users');
    if (resp.status === 401) {
      showAdminView(false);
      return;
    }
    rawStaffList = await resp.json();
    applyStaffFilterAndPagination();
  } catch (_) {}
}

function handleStaffSearch() {
  const input = document.getElementById('staffSearchInput');
  const btnClear = document.getElementById('btnStaffClearSearch');
  staffSearchKeyword = input.value.trim().toLowerCase();
  btnClear.style.display = staffSearchKeyword ? 'flex' : 'none';
  staffCurrentPage = 1;
  applyStaffFilterAndPagination();
}

function clearStaffSearch() {
  const input = document.getElementById('staffSearchInput');
  input.value = '';
  document.getElementById('btnStaffClearSearch').style.display = 'none';
  staffSearchKeyword = '';
  staffCurrentPage = 1;
  applyStaffFilterAndPagination();
}

function changeStaffPageSize() {
  staffPageSize = parseInt(document.getElementById('staffPageSize').value) || 10;
  staffCurrentPage = 1;
  applyStaffFilterAndPagination();
}

function goToStaffPage(page) {
  staffCurrentPage = page;
  applyStaffFilterAndPagination();
}

function applyStaffFilterAndPagination() {
  let filtered = rawStaffList;

  if (staffSearchKeyword) {
    filtered = rawStaffList.filter(u => {
      const name = (u.name || '').toLowerCase();
      const role = (u.role || '').toLowerCase();
      const pin = (u.pin || '').toLowerCase();
      return name.includes(staffSearchKeyword) || role.includes(staffSearchKeyword) || pin.includes(staffSearchKeyword);
    });
  }

  document.getElementById('userCount').textContent = rawStaffList.length;

  const totalItems = filtered.length;
  const totalPages = Math.ceil(totalItems / staffPageSize) || 1;

  if (staffCurrentPage > totalPages) staffCurrentPage = totalPages;
  if (staffCurrentPage < 1) staffCurrentPage = 1;

  const startIndex = (staffCurrentPage - 1) * staffPageSize;
  const pageItems = filtered.slice(startIndex, startIndex + staffPageSize);

  renderStaffTable(pageItems, totalItems, startIndex);
  renderPaginationFooter('staff', totalItems, startIndex, pageItems.length, totalPages, staffCurrentPage, goToStaffPage);
}

function renderStaffTable(users, totalFiltered, startIndex) {
  const tbody = document.getElementById('staffTableBody');

  if (!users.length) {
    const emptyMsg = staffSearchKeyword ? `ไม่พบข้อมูลที่ตรงกับคำค้นหา "${escapeHtml(staffSearchKeyword)}"` : 'ยังไม่มีข้อมูลเจ้าหน้าที่';
    tbody.innerHTML = `<tr><td colspan="7" class="empty">${emptyMsg}</td></tr>`;
    return;
  }

  tbody.innerHTML = users.map(u => {
    const status = u.status || 'active';
    const isSuspended = (status === 'suspended');
    const isActive = (status === 'active');
    const directUrl = `${window.BASE_URL}/?token=${u.token}`;

    let statusHtml = '';
    if (isSuspended) {
      statusHtml = `<span class="status-pill suspended">ระงับถาวร</span>`;
    } else if (isActive) {
      statusHtml = `<span class="status-pill active">อนุมัติแล้ว</span>`;
    } else {
      statusHtml = `<span class="status-pill disabled">ปิดชั่วคราว</span>`;
    }

    return `
      <tr style="${isSuspended ? 'opacity: 0.65;' : ''}">
        <td style="font-weight:600;white-space:nowrap;">
          <div style="display:inline-flex;align-items:center;gap:0.4rem;white-space:nowrap;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--brand-cyan);flex-shrink:0;"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
            <span style="white-space:nowrap;font-weight:600;">${escapeHtml(u.name)}</span>
          </div>
        </td>
        <td style="color:var(--text-secondary);font-size:0.82rem;">${escapeHtml(u.role || '-')}</td>
        <td style="font-family:'Plus Jakarta Sans',monospace;font-size:1.05rem;font-weight:700;letter-spacing:1px;color:var(--brand-cyan);">${escapeHtml(u.pin || '-')}</td>
        <td>${statusHtml}</td>
        <td style="font-size:0.75rem;color:var(--text-muted);">${u.last_used ? u.last_used.split(' ')[0] : 'ยังไม่เคยใช้'}</td>
        <td>
          <div class="action-group">
            <button class="btn-share-link" onclick="openShareLinkModal('${directUrl}', '${escapeJs(u.name)}')" title="เปิดแชร์ลิงก์">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
              <span>LINK</span>
            </button>
            <button class="btn-qr" onclick="showQrModal('${u.token}', '${escapeJs(u.name)}')" title="แสดง QR Code">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
              <span>QR</span>
            </button>
          </div>
        </td>
        <td>
          <div class="action-group">
            <button class="btn-edit" onclick="openEditStaffModal('${u.id}', '${escapeJs(u.name)}', '${escapeJs(u.role || '')}', '${escapeJs(u.pin || '')}')" title="แก้ไขข้อมูล & 6 PIN">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
              <span>แก้ไข</span>
            </button>
            ${isSuspended 
              ? `<button class="btn-reactivate" onclick="toggleStaffStatus('${u.id}')" title="คืนสิทธิ์การใช้งาน">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
                  <span>คืนสิทธิ์</span>
                </button>`
              : `<button class="btn-suspend" onclick="suspendStaff('${u.id}', '${escapeJs(u.name)}')" title="ระงับสิทธิ์เจ้าหน้าที่ (ไม่ลบออกจาก Log)">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line></svg>
                  <span>ระงับ</span>
                </button>`
            }
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function addStaff() {
  const name = document.getElementById('newStaffName').value.trim();
  const role = document.getElementById('newStaffRole').value.trim();
  const pin  = document.getElementById('newStaffPin').value.trim();
  const err  = document.getElementById('addError');
  err.textContent = '';

  if (!name) {
    err.textContent = 'กรุณาระบุชื่อเจ้าหน้าที่';
    return;
  }

  if (pin && !/^\d{6}$/.test(pin)) {
    err.textContent = 'รหัส 6 PIN ต้องเป็นตัวเลข 6 หลักพอดี (ห้ามใส่อย่างอื่น)';
    return;
  }

  try {
    const resp = await fetch('/api/admin/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, role, pin })
    });
    const data = await resp.json();

    if (data.success) {
      document.getElementById('newStaffName').value = '';
      document.getElementById('newStaffPin').value = '';
      loadStaffList();
      showAdminToast('สร้างสิทธิ์เจ้าหน้าที่สำเร็จ', 'success');
      openShareLinkModal(`${window.BASE_URL}/?token=${data.user.token}`, data.user.name);
    } else {
      err.textContent = data.message || 'บันทึกข้อมูลไม่สำเร็จ';
    }
  } catch (e) {
    err.textContent = 'เกิดข้อผิดพลาดในการเชื่อมต่อ';
  }
}

// ── Edit Staff Details & 6 PIN Modal ─────
function openEditStaffModal(userId, name, role, pin) {
  document.getElementById('editUserId').value = userId;
  document.getElementById('editUserName').value = name;
  document.getElementById('editUserRole').value = role;
  document.getElementById('editUserPin').value = pin;
  document.getElementById('editStaffModal').style.display = 'flex';
}

function closeEditStaffModal(e) {
  if (!e || e.target.id === 'editStaffModal' || e.target.classList.contains('btn-modal-close') || e.target.classList.contains('btn-modal-cancel')) {
    document.getElementById('editStaffModal').style.display = 'none';
  }
}

async function saveStaffEdit() {
  const userId = document.getElementById('editUserId').value;
  const name = document.getElementById('editUserName').value.trim();
  const role = document.getElementById('editUserRole').value.trim();
  const pin = document.getElementById('editUserPin').value.trim();

  if (!name) {
    alert('กรุณาระบุชื่อเจ้าหน้าที่');
    return;
  }

  if (pin && !/^\d{6}$/.test(pin)) {
    alert('รหัส 6 PIN ต้องเป็นตัวเลข 6 หลักเท่านั้น (ห้ามกรอกเกิน 6 หลัก หรือใส่อักขระอื่น)');
    return;
  }

  try {
    const resp = await fetch(`/api/admin/users/${userId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, role, pin })
    });
    const data = await resp.json();

    if (data.success) {
      closeEditStaffModal();
      loadStaffList();
      showAdminToast('อัปเดตข้อมูลเจ้าหน้าที่และ 6 PIN สำเร็จ', 'success');
    } else {
      alert(data.message || 'แก้ไขไม่สำเร็จ');
    }
  } catch (e) {
    alert('เกิดข้อผิดพลาดในการเชื่อมต่อ');
  }
}

// ── Soft Delete (Suspend) ────────────────
async function suspendStaff(userId, name) {
  if (!confirm(`ต้องการระงับสิทธิ์ของ "${name}" หรือไม่?\n(ข้อมูลจะไม่ถูกลบออกจากฐานข้อมูล และยังคงเก็บเป็น Log ไว้อ้างอิง)`)) return;
  try {
    const resp = await fetch(`/api/admin/users/${userId}`, { method: 'DELETE' });
    const data = await resp.json();
    if (data.success) {
      loadStaffList();
      showAdminToast(`ระงับสิทธิ์ "${name}" เรียบร้อยแล้ว`, 'success');
    }
  } catch (_) {}
}

async function toggleStaffStatus(userId) {
  try {
    const resp = await fetch(`/api/admin/users/${userId}/toggle`, { method: 'POST' });
    const data = await resp.json();
    if (data.success) {
      loadStaffList();
      showAdminToast('อัปเดตสถานะสำเร็จ', 'success');
    }
  } catch (_) {}
}

// ═════════════════════════════════════════
// 2. AUDIT LOGS (SEARCH & PAGINATION)
// ═════════════════════════════════════════
async function loadAuditLogs() {
  try {
    const resp = await fetch('/api/events');
    rawLogList = await resp.json();
    applyLogFilterAndPagination();
  } catch (_) {}
}

function handleLogSearch() {
  const input = document.getElementById('logSearchInput');
  const btnClear = document.getElementById('btnLogClearSearch');
  logSearchKeyword = input.value.trim().toLowerCase();
  btnClear.style.display = logSearchKeyword ? 'flex' : 'none';
  logCurrentPage = 1;
  applyLogFilterAndPagination();
}

function clearLogSearch() {
  const input = document.getElementById('logSearchInput');
  input.value = '';
  document.getElementById('btnLogClearSearch').style.display = 'none';
  logSearchKeyword = '';
  logCurrentPage = 1;
  applyLogFilterAndPagination();
}

function changeLogPageSize() {
  logPageSize = parseInt(document.getElementById('logPageSize').value) || 10;
  logCurrentPage = 1;
  applyLogFilterAndPagination();
}

function goToLogPage(page) {
  logCurrentPage = page;
  applyLogFilterAndPagination();
}

function applyLogFilterAndPagination() {
  let filtered = rawLogList;

  if (logSearchKeyword) {
    filtered = rawLogList.filter(e => {
      const user = (e.user_name || '').toLowerCase();
      const action = (e.action || '').toLowerCase();
      const detail = (e.detail || '').toLowerCase();
      const status = (e.status || '').toLowerCase();
      return user.includes(logSearchKeyword) || action.includes(logSearchKeyword) || detail.includes(logSearchKeyword) || status.includes(logSearchKeyword);
    });
  }

  const totalItems = filtered.length;
  const totalPages = Math.ceil(totalItems / logPageSize) || 1;

  if (logCurrentPage > totalPages) logCurrentPage = totalPages;
  if (logCurrentPage < 1) logCurrentPage = 1;

  const startIndex = (logCurrentPage - 1) * logPageSize;
  const pageItems = filtered.slice(startIndex, startIndex + logPageSize);

  renderAuditTable(pageItems);
  renderPaginationFooter('log', totalItems, startIndex, pageItems.length, totalPages, logCurrentPage, goToLogPage);
}

function renderAuditTable(logs) {
  const tbody = document.getElementById('auditTableBody');

  if (!logs.length) {
    const emptyMsg = logSearchKeyword ? `ไม่พบประวัติที่ตรงกับ "${escapeHtml(logSearchKeyword)}"` : 'ไม่มีประวัติการใช้งาน';
    tbody.innerHTML = `<tr><td colspan="5" class="empty">${emptyMsg}</td></tr>`;
    return;
  }

  tbody.innerHTML = logs.map(e => `
    <tr>
      <td style="white-space:nowrap;color:var(--text-muted);font-size:0.75rem;">${e.time}</td>
      <td style="font-weight:600;color:var(--brand-cyan);white-space:nowrap;">
        <div style="display:inline-flex;align-items:center;gap:0.3rem;white-space:nowrap;">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
          <span style="white-space:nowrap;">${escapeHtml(e.user_name || 'ไม่ระบุชื่อ')}</span>
        </div>
      </td>
      <td style="white-space:nowrap;font-size:0.75rem;">${e.action}</td>
      <td style="white-space:nowrap;">
        <span class="status-pill ${e.status === 'สำเร็จ' ? 'active' : 'disabled'}" style="font-size:0.68rem;padding:0.15rem 0.45rem;">
          ${e.status}
        </span>
      </td>
      <td style="font-size:0.72rem;color:var(--text-muted);max-width:125px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeHtml(e.detail)}">${escapeHtml(e.detail)}</td>
    </tr>
  `).join('');
}

// ═════════════════════════════════════════
// 3. PAGINATION CONTROLS GENERATOR
// ═════════════════════════════════════════
function renderPaginationFooter(prefix, totalItems, startIndex, countOnPage, totalPages, currentPage, onPageClick) {
  const footer = document.getElementById(`${prefix}PaginationFooter`);
  const info = document.getElementById(`${prefix}PaginationInfo`);
  const controls = document.getElementById(`${prefix}PaginationControls`);

  if (!footer || !info || !controls) return;

  if (totalItems === 0) {
    footer.style.display = 'none';
    return;
  }

  footer.style.display = 'flex';

  const endIdx = startIndex + countOnPage;
  const unit = (prefix === 'staff') ? 'คน' : 'รายการ';
  info.textContent = `แสดง ${startIndex + 1} - ${endIdx} จากทั้งหมด ${totalItems} ${unit} (หน้า ${currentPage}/${totalPages})`;

  if (totalPages <= 1) {
    controls.innerHTML = '';
    return;
  }

  let html = '';

  // Previous button
  html += `<button class="btn-page" ${currentPage === 1 ? 'disabled' : ''} onclick="${onPageClick.name}(${currentPage - 1})" title="หน้าก่อนหน้า">‹</button>`;

  // Page Numbers with smart ellipsis
  let startP = Math.max(1, currentPage - 2);
  let endP = Math.min(totalPages, currentPage + 2);

  if (startP > 1) {
    html += `<button class="btn-page" onclick="${onPageClick.name}(1)">1</button>`;
    if (startP > 2) html += `<span style="color:var(--text-muted);padding:0 2px;">...</span>`;
  }

  for (let p = startP; p <= endP; p++) {
    html += `<button class="btn-page ${p === currentPage ? 'active' : ''}" onclick="${onPageClick.name}(${p})">${p}</button>`;
  }

  if (endP < totalPages) {
    if (endP < totalPages - 1) html += `<span style="color:var(--text-muted);padding:0 2px;">...</span>`;
    html += `<button class="btn-page" onclick="${onPageClick.name}(${totalPages})">${totalPages}</button>`;
  }

  // Next button
  html += `<button class="btn-page" ${currentPage === totalPages ? 'disabled' : ''} onclick="${onPageClick.name}(${currentPage + 1})" title="หน้าถัดไป">›</button>`;

  controls.innerHTML = html;
}

// ═════════════════════════════════════════
// 4. MODALS (SHARE & QR)
// ═════════════════════════════════════════
function openShareLinkModal(url, staffName) {
  document.getElementById('shareModalTitle').textContent = `ลิงก์เข้าใช้งาน: ${staffName}`;
  document.getElementById('shareUrlInput').value = url;
  
  const lineShareText = encodeURIComponent(`[ลิงก์เปิดไม้กั้นสำหรับ ${staffName}]\nแตะลิงก์เพื่อเข้าใช้งานได้ทันที:\n${url}`);
  const btnLine = document.getElementById('btnSendLine');
  if (btnLine) {
    btnLine.href = `https://line.me/R/msg/text/?${lineShareText}`;
  }

  document.getElementById('shareLinkModal').style.display = 'flex';
}

function closeShareLinkModal(e) {
  if (!e || e.target.id === 'shareLinkModal' || e.target.classList.contains('btn-modal-close')) {
    document.getElementById('shareLinkModal').style.display = 'none';
  }
}

function copyShareUrl() {
  const input = document.getElementById('shareUrlInput');
  if (input) {
    input.select();
    input.setSelectionRange(0, 99999);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(input.value).then(() => {
        showAdminToast('คัดลอกลิงก์สำเร็จแล้ว!', 'success');
      });
    } else {
      document.execCommand('copy');
      showAdminToast('คัดลอกลิงก์สำเร็จแล้ว!', 'success');
    }
  }
}

async function showQrModal(token, staffName) {
  document.getElementById('qrModalTitle').textContent = `QR Code: ${staffName}`;
  document.getElementById('qrImage').src = '';
  document.getElementById('qrModal').style.display = 'flex';

  try {
    const resp = await fetch(`/api/admin/qrcode/${token}`);
    const data = await resp.json();
    document.getElementById('qrImage').src = data.qrcode;
  } catch (_) {}
}

function closeQrModal(e) {
  if (!e || e.target.id === 'qrModal' || e.target.classList.contains('btn-modal-close')) {
    document.getElementById('qrModal').style.display = 'none';
  }
}

// ── Helpers ──────────────────────────────
function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[m]);
}

function escapeJs(str) {
  if (!str) return '';
  return String(str).replace(/['"\\]/g, '\\$&');
}

// ── Real-Time Sync Listeners ─────────────
try {
  if (typeof BroadcastChannel !== 'undefined') {
    const adminBc = new BroadcastChannel('mth_gate_channel');
    adminBc.onmessage = (event) => {
      if (event.data && event.data.type === 'GATE_OPENED') {
        loadAuditLogs();
        loadStaffList();
      }
    };
  }
} catch (_) {}

window.addEventListener('storage', (e) => {
  if (e.key === 'mth_gate_event_trigger') {
    loadAuditLogs();
    loadStaffList();
  }
});

// ── Init ────────────────────────────────
(function init() {
  initAdminTheme();
  showAdminView(window.IS_ADMIN_LOGGED);
})();

