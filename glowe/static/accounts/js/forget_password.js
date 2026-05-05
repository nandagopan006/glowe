// ── INJECT KEYFRAMES ──
const _style = document.createElement('style');
_style.textContent = `
  @keyframes tIn   { to { transform:translateY(0); opacity:1; } }
  @keyframes tOut  { to { transform:translateY(-80px); opacity:0; } }
  @keyframes tProg { from{width:100%} to{width:0%} }
`;
document.head.appendChild(_style);

// ── BLOB SVG ──
function blobSVG(c1, c2, c3) {
  return `<svg viewBox="0 0 42 60" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="10" cy="10" rx="18" ry="14" fill="${c1}" opacity="0.45"/>
    <ellipse cx="34" cy="46" rx="14" ry="12" fill="${c2}" opacity="0.35"/>
    <ellipse cx="20" cy="30" rx="10" ry="8"  fill="${c3}" opacity="0.3"/>
    <ellipse cx="5"  cy="50" rx="9"  ry="7"  fill="${c1}" opacity="0.22"/>
  </svg>`;
}

// ── TOAST CONFIG ──
const CONFIGS = {
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

// ── ON LOAD — show error toast if django returned error ──
window.addEventListener('load', () => {
  const errorEl = document.getElementById('form-error');
  if (errorEl) {
    const msg = errorEl.textContent.trim();
    if (msg.toLowerCase().includes('verified')) {
      showToast('warning', 'Not Verified', msg);
    } else {
      showToast('error', 'Not Found', msg);
    }
  }
});

// ── SUBMIT BUTTON LOADING STATE ──
document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form');
  const btn  = document.querySelector('button[type="submit"]');

  if (!form || !btn) return;

  form.addEventListener('submit', (e) => {
    // if email input is empty, let browser handle it — don't show loader
    const emailInput = document.getElementById('email');
    if (!emailInput || !emailInput.value.trim()) return;

    // store original button content to restore if needed
    const originalHTML = btn.innerHTML;

    // switch button to loading state
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
        margin: 0 6px;
      ">Sending</span>
      <span style="display:flex;align-items:center;gap:3px;">
        <span class="btn-dot"></span>
        <span class="btn-dot"></span>
        <span class="btn-dot"></span>
      </span>
    `;

    // safety fallback — restore button after 8s if page hasn't redirected
    // (handles cases where server returns error and page reloads)
    setTimeout(() => {
      btn.classList.remove('btn-loading');
      btn.innerHTML = originalHTML;
    }, 8000);
  });
});