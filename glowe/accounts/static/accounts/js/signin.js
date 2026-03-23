// ── INJECT KEYFRAMES ──
const _style = document.createElement('style');
_style.textContent = `
  @keyframes toastIn  { to { transform:translateY(0); opacity:1; } }
  @keyframes toastOut { to { transform:translateY(-80px); opacity:0; } }
  @keyframes toastProg { from{width:100%} to{width:0%} }
  @keyframes btnDotBounce {
    0%, 80%, 100% { transform:translateY(0);   opacity:0.5; }
    40%            { transform:translateY(-5px); opacity:1;   }
  }
  .btn-loader { display:inline-flex; align-items:center; gap:4px; }
  .btn-loader.hidden { display:none !important; }
  .btn-loader span {
    display:inline-block; width:5px; height:5px; border-radius:50%;
    background:#f5f2ed; animation:btnDotBounce 0.9s ease-in-out infinite;
  }
  .btn-loader span:nth-child(1) { animation-delay:0s; }
  .btn-loader span:nth-child(2) { animation-delay:0.18s; }
  .btn-loader span:nth-child(3) { animation-delay:0.36s; }
`;
document.head.appendChild(_style);

// ── TOAST CONTAINER ──
const _toastContainer = document.createElement('div');
_toastContainer.style.cssText = `
  position:fixed; top:20px; left:50%; transform:translateX(-50%);
  z-index:99999; display:flex; flex-direction:column;
  align-items:center; gap:8px; pointer-events:none;
`;
document.body.appendChild(_toastContainer);

// ── TOAST CONFIG ──
const TOAST_CONFIG = {
  success: {
    icon: '✓', blobs: ['#3aaa72','#1a6644','#0d4a30'],
    bg: '#1e3d2f', blobBg: '#172f24',
    iconBg: 'radial-gradient(circle,#3aaa72,#1a6644)',
    label: '#6ee7a8', title: '#f0fdf4', msg: '#bbf7d0', progress: '#4ade80',
  },
  error: {
    icon: '✕', blobs: ['#e05050','#a82020','#7a1010'],
    bg: '#3d1e1e', blobBg: '#2f1717',
    iconBg: 'radial-gradient(circle,#e05050,#a82020)',
    label: '#fca5a5', title: '#fff1f2', msg: '#fecaca', progress: '#f87171',
  },
  warning: {
    icon: '!', blobs: ['#f59e0b','#b45309','#7c2d00'],
    bg: '#3d2000', blobBg: '#2e1800',
    iconBg: 'radial-gradient(circle,#f59e0b,#b45309)',
    label: '#fcd34d', title: '#fff8e1', msg: '#fde68a', progress: '#f59e0b',
  },
  info: {
    icon: '↺', blobs: ['#2dd4bf','#0f766e','#0a4a45'],
    bg: '#0f2d2a', blobBg: '#0a2220',
    iconBg: 'radial-gradient(circle,#2dd4bf,#0f766e)',
    label: '#5eead4', title: '#f0fdfa', msg: '#99f6e4', progress: '#2dd4bf',
  },
};

// ── BLOB SVG ──
function makeBlobSVG(c) {
  return `<svg viewBox="0 0 50 70" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="12" cy="12" rx="20" ry="16" fill="${c[0]}" opacity="0.45"/>
    <ellipse cx="40" cy="52" rx="16" ry="14" fill="${c[1]}" opacity="0.35"/>
    <ellipse cx="24" cy="34" rx="11" ry="9"  fill="${c[2]}" opacity="0.3"/>
    <ellipse cx="6"  cy="56" rx="10" ry="8"  fill="${c[0]}" opacity="0.22"/>
  </svg>`;
}

// ── SHOW TOAST ──
function showToast(type, title, message) {
  const c = TOAST_CONFIG[type] || TOAST_CONFIG.info;
  const toast = document.createElement('div');
  toast.style.cssText = `
    pointer-events:all; display:flex; align-items:center; width:300px;
    border-radius:14px; overflow:hidden; position:relative;
    background:${c.bg};
    box-shadow:0 10px 32px rgba(42,31,20,0.2),0 2px 8px rgba(42,31,20,0.10);
    animation:toastIn 0.5s cubic-bezier(0.34,1.56,0.64,1) forwards;
    transform:translateY(-80px); opacity:0;
  `;
  toast.innerHTML = `
    <div style="width:54px;min-width:54px;align-self:stretch;position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden;background:${c.blobBg};">
      ${makeBlobSVG(c.blobs)}
      <div style="width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:#fff;z-index:2;position:relative;background:${c.iconBg};flex-shrink:0;box-shadow:0 2px 8px rgba(0,0,0,0.2);">
        ${c.icon}
      </div>
    </div>
    <div style="flex:1;padding:10px 6px 10px 10px;">
      <p style="font-family:'Montserrat',sans-serif;font-size:7px;font-weight:600;letter-spacing:0.2em;text-transform:uppercase;margin:0 0 2px;color:${c.label};opacity:0.85;">${type}</p>
      <p style="font-family:'Cormorant Garamond',serif;font-size:16px;font-weight:700;line-height:1.2;margin:0 0 2px;color:${c.title};">${title}</p>
      <p style="font-family:'Montserrat',sans-serif;font-size:9px;font-weight:400;line-height:1.5;margin:0;color:${c.msg};opacity:0.85;">${message}</p>
    </div>
    <button onclick="dismissToast(this.parentElement)" style="background:none;border:none;cursor:pointer;font-size:10px;padding:6px 10px 0 0;align-self:flex-start;color:#fff;opacity:0.4;">✕</button>
    <div style="position:absolute;bottom:0;left:0;height:2px;border-radius:0 2px 0 0;background:${c.progress};animation:toastProg 3s linear forwards;"></div>
  `;
  _toastContainer.appendChild(toast);
  toast._timer = setTimeout(() => dismissToast(toast), 3000);
}

// ── DISMISS TOAST ──
function dismissToast(toast) {
  if (!toast || toast._dismissed) return;
  toast._dismissed = true;
  clearTimeout(toast._timer);
  toast.style.animation = 'toastOut 0.35s cubic-bezier(0.4,0,1,1) forwards';
  setTimeout(() => toast.remove(), 350);
}

// ── TOGGLE PASSWORD ──
function togglePwd(id, btn) {
  const input = document.getElementById(id);
  const isHidden = input.type === 'password';
  input.type = isHidden ? 'text' : 'password';
  btn.innerHTML = isHidden
    ? `<svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`
    : `<svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;
}

// ── BUTTON ELEMENTS ──
const signinBtn       = document.getElementById('signin-btn');
const signinBtnLabel  = document.getElementById('signin-btn-label');
const signinBtnArrow  = document.getElementById('signin-btn-arrow');
const signinBtnLoader = document.getElementById('signin-btn-loader');

function showBtnLoader() {
  signinBtnLabel.textContent = 'Signing In';
  signinBtnArrow.classList.add('hidden');
  signinBtnLoader.classList.remove('hidden');
  signinBtn.disabled = true;
  signinBtn.style.opacity = '0.85';
  signinBtn.style.cursor  = 'not-allowed';
}

function resetBtn() {
  signinBtnLabel.textContent = 'Sign In';
  signinBtnArrow.classList.remove('hidden');
  signinBtnLoader.classList.add('hidden');
  signinBtn.disabled = false;
  signinBtn.style.opacity = '1';
  signinBtn.style.cursor  = 'pointer';
}

// ── FORM SUBMIT — show loader ──
document.getElementById('signin-form').addEventListener('submit', () => {
  showBtnLoader();
});

// ── ON PAGE LOAD ──
document.addEventListener('DOMContentLoaded', () => {
  const errorEl   = document.getElementById('django-error');
  const successEl = document.getElementById('django-success');
  const updatePasswordEl = document.getElementById('django-update-password'); // ✅ add

  if (errorEl) {
    // ✅ validation failed — reset button back to normal, show error toast
    resetBtn();
    showToast('error', 'Sign In Failed', errorEl.textContent.trim());
  }

  if (successEl) {
    showToast('success', 'Account Created!', successEl.textContent.trim());
  }
   if (updatePasswordEl) showToast('success', 'Password Updated!',    updatePasswordEl.textContent.trim());
});