// ── GET ELEMENTS ──
const inputs      = document.querySelectorAll('.otp-input');
const hiddenInput = document.getElementById('otp-hidden');
const otpBoxes    = document.getElementById('otp-boxes');
const resendBtn   = document.getElementById('resend-btn');
const timerEl     = document.getElementById('timer');

// ── INJECT KEYFRAMES ──
const _style = document.createElement('style');
_style.textContent = `
  @keyframes toastIn  { to { transform:translateY(0); opacity:1; } }
  @keyframes toastOut { to { transform:translateY(-80px); opacity:0; } }
  @keyframes toastProg { from{width:100%} to{width:0%} }
`;
document.head.appendChild(_style);

// ── TOAST CONFIG ──
const TOAST_CONFIG = {
  success: {
    cls:      't-success',
    icon:     '✓',
    blobs:    ['#3aaa72','#1a6644','#0d4a30'],
    bg:       '#1e3d2f',
    blobBg:   '#172f24',
    iconBg:   'radial-gradient(circle,#3aaa72,#1a6644)',
    label:    '#6ee7a8',
    title:    '#f0fdf4',
    msg:      '#bbf7d0',
    progress: '#4ade80',
  },
  error: {
    cls:      't-error',
    icon:     '✕',
    blobs:    ['#e05050','#a82020','#7a1010'],
    bg:       '#3d1e1e',
    blobBg:   '#2f1717',
    iconBg:   'radial-gradient(circle,#e05050,#a82020)',
    label:    '#fca5a5',
    title:    '#fff1f2',
    msg:      '#fecaca',
    progress: '#f87171',
  },
  warning: {
    cls:      't-warning',
    icon:     '!',
    blobs:    ['#f59e0b','#b45309','#7c2d00'],
    bg:       '#3d2000',
    blobBg:   '#2e1800',
    iconBg:   'radial-gradient(circle,#f59e0b,#b45309)',
    label:    '#fcd34d',
    title:    '#fff8e1',
    msg:      '#fde68a',
    progress: '#f59e0b',
  },
  info: {
    cls:      't-info',
    icon:     '↺',
    blobs:    ['#2dd4bf','#0f766e','#0a4a45'],
    bg:       '#0f2d2a',
    blobBg:   '#0a2220',
    iconBg:   'radial-gradient(circle,#2dd4bf,#0f766e)',
    label:    '#5eead4',
    title:    '#f0fdfa',
    msg:      '#99f6e4',
    progress: '#2dd4bf',
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
  const c         = TOAST_CONFIG[type];
  const container = document.getElementById('toastContainer');

  const toast = document.createElement('div');
  toast.style.cssText = `
    pointer-events:all;
    display:flex;
    align-items:center;
    width:280px;
    border-radius:14px;
    overflow:hidden;
    position:relative;
    background:${c.bg};
    box-shadow:0 10px 32px rgba(42,31,20,0.2),0 2px 8px rgba(42,31,20,0.10);
    animation:toastIn 0.5s cubic-bezier(0.34,1.56,0.64,1) forwards;
    transform:translateY(-80px);
    opacity:0;
  `;

  toast.innerHTML = `
    <div style="width:50px;min-width:50px;align-self:stretch;position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden;background:${c.blobBg};">
      ${makeBlobSVG(c.blobs)}
      <div style="width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;z-index:2;position:relative;box-shadow:0 2px 8px rgba(0,0,0,0.2);background:${c.iconBg};flex-shrink:0;">
        ${c.icon}
      </div>
    </div>
    <div style="flex:1;padding:9px 4px 9px 8px;">
      <p style="font-family:'Montserrat',sans-serif;font-size:7px;font-weight:600;letter-spacing:0.2em;text-transform:uppercase;margin:0 0 1px;color:${c.label};opacity:0.85;">${type}</p>
      <p style="font-family:'Cormorant Garamond',serif;font-size:15px;font-weight:700;line-height:1.2;margin:0 0 2px;color:${c.title};">${title}</p>
      <p style="font-family:'Montserrat',sans-serif;font-size:9px;font-weight:400;line-height:1.5;margin:0;color:${c.msg};opacity:0.85;">${message}</p>
    </div>
    <button onclick="dismissToast(this.parentElement)" style="background:none;border:none;cursor:pointer;font-size:10px;padding:6px 10px 0 0;align-self:flex-start;color:#fff;opacity:0.4;">✕</button>
    <div style="position:absolute;bottom:0;left:0;height:2px;border-radius:0 2px 0 0;background:${c.progress};animation:toastProg 2s linear forwards;"></div>
  `;

  container.appendChild(toast);
  toast._timer = setTimeout(() => dismissToast(toast), 2000);
}

// ── DISMISS TOAST ──
function dismissToast(toast) {
  if (!toast || toast._dismissed) return;
  toast._dismissed = true;
  clearTimeout(toast._timer);
  toast.style.animation = 'toastOut 0.35s cubic-bezier(0.4,0,1,1) forwards';
  setTimeout(() => toast.remove(), 350);
}

// ── TYPING IN BOX ──
inputs.forEach((input, index) => {

  input.addEventListener('input', () => {
    input.value = input.value.replace(/[^0-9]/g, '');

    // clear error state on all boxes when user starts typing
    inputs.forEach(i => i.classList.remove('error-box'));

    if (input.value) {
      input.classList.add('filled');
      if (index < inputs.length - 1) inputs[index + 1].focus();
    } else {
      input.classList.remove('filled');
    }
    hiddenInput.value = Array.from(inputs).map(i => i.value).join('');
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace' && !input.value && index > 0) {
      inputs[index - 1].focus();
      inputs[index - 1].value = '';
      inputs[index - 1].classList.remove('filled');
    }
  });

  input.addEventListener('paste', (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/[^0-9]/g, '');
    [...pasted].forEach((char, i) => {
      if (inputs[i]) {
        inputs[i].value = char;
        inputs[i].classList.add('filled');
      }
    });
    hiddenInput.value = Array.from(inputs).map(i => i.value).join('');
  });

});

// ── VERIFY BUTTON LOADER ──
const verifyBtn       = document.getElementById('verify-btn');
const verifyBtnLabel  = document.getElementById('verify-btn-label');
const verifyBtnArrow  = document.getElementById('verify-btn-arrow');
const verifyBtnLoader = document.getElementById('verify-btn-loader');

document.getElementById('otp-form').addEventListener('submit', () => {
  const otp = hiddenInput.value;
  if (otp.length === 4) {
    // show loader, hide label + arrow
    verifyBtnLabel.textContent  = 'Verifying';
    verifyBtnArrow.classList.add('hidden');
    verifyBtnLoader.classList.remove('hidden');
    verifyBtn.disabled = true;
    verifyBtn.style.opacity = '0.85';
    verifyBtn.style.cursor  = 'not-allowed';
  }
});

// ── RESEND LOADER ──
const resendLabel  = document.getElementById('resend-label');
const resendLoader = document.getElementById('resend-loader');

resendBtn.addEventListener('click', (e) => {
  if (resendBtn.classList.contains('pointer-events-none')) return;
  // show loader on resend
  resendLabel.textContent = 'Sending';
  resendLoader.classList.remove('hidden');
  resendBtn.style.pointerEvents = 'none';
});

// ── PAGE LOAD — show correct toast ──
window.addEventListener('load', () => {
  const errorEl   = document.querySelector('.text-red-500');
  const successEl = document.getElementById('otp-success-msg');

  if (errorEl) {
    // re-fill boxes from submitted OTP value on error
    const submitted = hiddenInput.value || '';
    [...submitted].forEach((char, i) => {
      if (inputs[i]) {
        inputs[i].value = char;
        inputs[i].classList.add('filled');
      }
    });

    otpBoxes.classList.add('shake');
    inputs.forEach(i => i.classList.add('error-box'));
    setTimeout(() => otpBoxes.classList.remove('shake'), 500);
    showToast('error', 'Invalid OTP', errorEl.textContent.trim());

  } else if (successEl) {
    const msg      = successEl.textContent.trim();
    const isResend = msg.toLowerCase().includes('new');
    showToast(
      isResend ? 'info'        : 'success',
      isResend ? 'OTP Resent!' : 'OTP Sent!',
      msg
    );
  }
});

// ── TIMER ──
let seconds = typeof SECONDS_LEFT !== 'undefined' ? SECONDS_LEFT : 60;

const initM = String(Math.floor(seconds / 60)).padStart(2, '0');
const initS = String(seconds % 60).padStart(2, '0');
timerEl.textContent = `${initM}:${initS} remaining`;

if (seconds <= 0) {
  timerEl.textContent = 'OTP expired';
  resendBtn.classList.remove('pointer-events-none', 'opacity-40');
  showToast('warning', 'OTP Expired', 'Please request a new verification code.');
}

const timerInterval = setInterval(() => {
  seconds--;

  const m = String(Math.floor(seconds / 60)).padStart(2, '0');
  const s = String(seconds % 60).padStart(2, '0');
  timerEl.textContent = `${m}:${s} remaining`;

  if (seconds <= 0) {
    clearInterval(timerInterval);
    timerEl.textContent = 'OTP expired';
    resendBtn.classList.remove('pointer-events-none', 'opacity-40');
    showToast('warning', 'OTP Expired', 'Please request a new verification code.');
  }

}, 1000);

// ── RESEND CLICK — disable after click ──
resendBtn.addEventListener('click', () => {
  resendBtn.classList.add('pointer-events-none', 'opacity-40');
});