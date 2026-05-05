// ── TOGGLE PASSWORD VISIBILITY ──
function togglePwd(id, btn) {
  const input    = document.getElementById(id);
  const isHidden = input.type === 'password';
  input.type     = isHidden ? 'text' : 'password';
  btn.innerHTML  = isHidden
    ? `<svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`
    : `<svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;
}

// ── BLOB SVG ──
function blobSVG(c1, c2, c3) {
  return `<svg viewBox="0 0 50 70" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="12" cy="12" rx="20" ry="16" fill="${c1}" opacity="0.45"/>
    <ellipse cx="40" cy="52" rx="16" ry="14" fill="${c2}" opacity="0.35"/>
    <ellipse cx="24" cy="34" rx="11" ry="9"  fill="${c3}" opacity="0.3"/>
    <ellipse cx="6"  cy="56" rx="10" ry="8"  fill="${c1}" opacity="0.22"/>
  </svg>`;
}

// ── TOAST CONFIG ──
const CONFIGS = {
  success: {
    bg:'#1e3d2f', blobBg:'#172f24',
    iconBg:'radial-gradient(circle,#3aaa72,#1a6644)',
    icon:'✓', label:'#6ee7a8', titleC:'#f0fdf4',
    msgC:'#bbf7d0', prog:'#4ade80',
    b1:'#3aaa72', b2:'#1a6644', b3:'#0d4a30'
  },
  error: {
    bg:'#3d1e1e', blobBg:'#2f1717',
    iconBg:'radial-gradient(circle,#e05050,#a82020)',
    icon:'!', label:'#fca5a5', titleC:'#fff1f2',
    msgC:'#fecaca', prog:'#f87171',
    b1:'#e05050', b2:'#a82020', b3:'#7a1010'
  },
  warning: {
    bg:'#3d2000', blobBg:'#2e1800',
    iconBg:'radial-gradient(circle,#f59e0b,#b45309)',
    icon:'!', label:'#fcd34d', titleC:'#fff8e1',
    msgC:'#fde68a', prog:'#f59e0b',
    b1:'#f59e0b', b2:'#b45309', b3:'#7c2d00'
  },
};

// ── SHOW TOAST ──
function showToast(type, title, message) {
  const c         = CONFIGS[type];
  const container = document.getElementById('toastContainer');
  const toast     = document.createElement('div');
  toast.className = 'toast';
  toast.style.background = c.bg;
  toast.innerHTML = `
    <div style="width:40px;min-width:40px;align-self:stretch;position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden;background:${c.blobBg};">
      ${blobSVG(c.b1, c.b2, c.b3)}
      <div style="width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:#fff;z-index:2;position:relative;background:${c.iconBg};">${c.icon}</div>
    </div>
    <div style="flex:1;padding:7px 3px 7px 7px;">
      <p style="font-family:'Montserrat',sans-serif;font-size:7px;font-weight:600;letter-spacing:0.2em;text-transform:uppercase;margin:0 0 1px;color:${c.label};">${type}</p>
      <p style="font-family:'Cormorant Garamond',serif;font-size:13px;font-weight:700;margin:0 0 1px;color:${c.titleC};line-height:1.2;">${title}</p>
      <p style="font-family:'Montserrat',sans-serif;font-size:8.5px;margin:0;color:${c.msgC};opacity:0.85;line-height:1.4;">${message}</p>
    </div>
    <button onclick="dismiss(this.parentElement)" style="background:none;border:none;cursor:pointer;font-size:9px;padding:5px 8px 0 0;align-self:flex-start;color:#fff;opacity:0.4;">✕</button>
    <div style="position:absolute;bottom:0;left:0;height:2px;background:${c.prog};animation:tProg 5s linear forwards;"></div>
  `;
  container.appendChild(toast);
  toast._timer = setTimeout(() => dismiss(toast), 5000);
}

// ── DISMISS ──
function dismiss(toast) {
  if (!toast || toast._d) return;
  toast._d = true;
  clearTimeout(toast._timer);
  toast.classList.add('hide');
  setTimeout(() => toast.remove(), 350);
}

// ── ON LOAD — read django error messages ──
window.addEventListener('load', () => {
  const errorEl = document.getElementById('form-error');
  if (errorEl) {
    const msg = errorEl.textContent.trim();
    if (msg.toLowerCase().includes('match')) {
      showToast('warning', 'Mismatch!', msg);
    } else if (msg.toLowerCase().includes('upper') || msg.toLowerCase().includes('password')) {
      showToast('error', 'Weak Password', msg);
    } else {
      showToast('error', 'Error', msg);
    }
  }
});

// ── SUBMIT — validate first, show loading ONLY if all conditions pass ──
document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form');
  const btn  = document.querySelector('button[type="submit"]');

  if (!form || !btn) return;

  // same pattern as django view validation
  const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;

  form.addEventListener('submit', (e) => {
    const newPassword     = document.getElementById('new_password').value;
    const confirmPassword = document.getElementById('confirm_password').value;

    // ── CHECK 1: password strength ──
    if (!passwordPattern.test(newPassword)) {
      e.preventDefault(); // stop form submit
      showToast('error', 'Weak Password', 'Must contain upper, lower, number (8+ chars)');
      return; // no loading — condition failed
    }

    // ── CHECK 2: passwords match ──
    if (newPassword !== confirmPassword) {
      e.preventDefault(); // stop form submit
      showToast('warning', 'Mismatch!', 'Passwords do not match.');
      return; // no loading — condition failed
    }

    // ── ALL CHECKS PASSED — show loading ──
    const originalHTML = btn.innerHTML;
    btn.classList.add('btn-loading');
    btn.innerHTML = `
      <span class="btn-spinner"></span>
      <span style="
        font-family:'Montserrat',sans-serif;
        font-size:10px;
        font-weight:600;
        letter-spacing:0.18em;
        text-transform:uppercase;
        color:#f5f2ed;
        margin:0 6px;
      ">Updating</span>
      <span style="display:flex;align-items:center;gap:3px;">
        <span class="btn-dot"></span>
        <span class="btn-dot"></span>
        <span class="btn-dot"></span>
      </span>
    `;

    // safety fallback — restore button after 8s if something goes wrong
    setTimeout(() => {
      btn.classList.remove('btn-loading');
      btn.innerHTML = originalHTML;
    }, 8000);
  });
});