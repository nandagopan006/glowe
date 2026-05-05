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

// ── ON LOAD — read all django messages and show correct toast ──
window.addEventListener('load', () => {
  const maxReachedEl = document.getElementById('form-max-reached'); // max attempts reached marker
  const warningEl    = document.getElementById('form-warning');     // warning — blocked message
  const errorEl      = document.getElementById('form-error');       // error — generic error
  const successEl    = document.getElementById('form-success');     // success — resend worked

  // ── CASE 1: max attempts reached — show no toast at all ──
  // user already sees the "Max attempts reached" button on page
  if (maxReachedEl) return;

  // ── CASE 2: warning — user is blocked (too many attempts) ──
  // comes from messages.warning() in resend_reset_email view
  if (warningEl) {
    setTimeout(() => {
      showToast('warning', 'Blocked!', warningEl.textContent.trim());
    }, 400);

  // ── CASE 3: error — generic error ──
  } else if (errorEl) {
    setTimeout(() => {
      showToast('error', 'Error', errorEl.textContent.trim());
    }, 400);

  // ── CASE 4: success — resend email was sent successfully ──
  // comes from messages.success() in resend_reset_email view
  } else if (successEl) {
    setTimeout(() => {
      showToast('success', 'Email Sent!', successEl.textContent.trim());
    }, 600);

  // ── CASE 5: no message — fresh first-time arrival from forget_password page ──
  } else {
    setTimeout(() => {
      showToast('success', 'Email Sent!', 'Reset link sent to your inbox.');
    }, 600);
  }
});