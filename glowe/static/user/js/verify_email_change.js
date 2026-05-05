// ── OTP BOX MOVE FORWARD ──
function otpMove(input, index) {
  const val = input.value.replace(/\D/g, ''); // digits only
  input.value = val;
  if (val) {
    input.classList.add('filled');
    if (index < 3) document.getElementById(`otp${index + 1}`).focus();
  } else {
    input.classList.remove('filled');
  }
}

// ── OTP BOX MOVE BACK ──
function otpBack(e, index) {
  if (e.key === 'Backspace' && !document.getElementById(`otp${index}`).value && index > 0) {
    document.getElementById(`otp${index - 1}`).focus();
  }
}

// ── PASTE SUPPORT ──
document.querySelectorAll('.otp-input').forEach((input, i) => {
  input.addEventListener('paste', e => {
    e.preventDefault();
    const paste = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '').slice(0, 4);
    paste.split('').forEach((ch, idx) => {
      const box = document.getElementById(`otp${idx}`);
      if (box) { box.value = ch; box.classList.add('filled'); }
    });
    const last = document.getElementById(`otp${Math.min(paste.length - 1, 3)}`);
    if (last) last.focus();
  });
});

// ── BUILD OTP + LOADING ──
// loading only shows when: all 4 digits entered AND timer not expired
function buildOtp(e) {
  const otp = [0, 1, 2, 3].map(i => document.getElementById(`otp${i}`).value).join('');

  // condition 1 — not all 4 digits entered
  if (otp.length < 4) {
    e.preventDefault();
    [0, 1, 2, 3].forEach(i => {
      const el = document.getElementById(`otp${i}`);
      el.classList.add('error');
      setTimeout(() => el.classList.remove('error'), 600);
    });
    showToast('error', 'Incomplete', 'Please enter all 4 digits.');
    return;
  }

  // condition 2 — timer expired
  if (seconds <= 0) {
    e.preventDefault();
    showToast('error', 'Expired', 'Code has expired. Please click Resend.');
    return;
  }

  // ── all good — set otp and show loading ──
  document.getElementById('otpHidden').value = otp;

  const btn = document.getElementById('verifyBtn');
  btn.classList.add('btn-loading');
  document.getElementById('verifyBtnContent').innerHTML = `
    <span class="btn-spinner"></span>
    <span style="font-family:'Montserrat',sans-serif;font-size:10px;font-weight:600;letter-spacing:0.16em;text-transform:uppercase;">
      Verifying...
    </span>
  `;
  // form submits naturally after this
}

// ── COUNTDOWN TIMER ──
// seconds_left is passed from Django via window.SECONDS_LEFT in the HTML
let seconds = window.SECONDS_LEFT || 0;
const timerEl = document.getElementById('timer');
const interval = setInterval(() => {
  seconds--;
  if (seconds <= 0) {
    timerEl.textContent = 'Expired';
    timerEl.style.color = '#c0392b';
    clearInterval(interval);
  } else {
    timerEl.textContent = seconds + 's';
  }
}, 1000);

// ── TOAST ──
const T_CONFIGS = {
  success: { bg:'#1e3d2f', iconBg:'radial-gradient(circle,#3aaa72,#1a6644)', icon:'✓', label:'#6ee7a8', titleC:'#f0fdf4', msgC:'#bbf7d0', prog:'#4ade80' },
  error:   { bg:'#3d1e1e', iconBg:'radial-gradient(circle,#e05050,#a82020)', icon:'!', label:'#fca5a5', titleC:'#fff1f2', msgC:'#fecaca', prog:'#f87171' },
  warning: { bg:'#3d2000', iconBg:'radial-gradient(circle,#f59e0b,#b45309)', icon:'!', label:'#fcd34d', titleC:'#fff8e1', msgC:'#fde68a', prog:'#f59e0b' },
};
function showToast(type, title, message) {
  const c = T_CONFIGS[type] || T_CONFIGS.error;
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.style.background = c.bg;
  toast.innerHTML = `
    <div style="width:40px;min-width:40px;align-self:stretch;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.12);">
      <div style="width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:#fff;background:${c.iconBg};">${c.icon}</div>
    </div>
    <div style="flex:1;padding:8px 4px 8px 8px;">
      <p style="font-family:'Montserrat',sans-serif;font-size:7px;font-weight:600;letter-spacing:0.2em;text-transform:uppercase;margin:0 0 1px;color:${c.label};">${type}</p>
      <p style="font-family:'Cormorant Garamond',serif;font-size:13px;font-weight:700;margin:0 0 1px;color:${c.titleC};line-height:1.2;">${title}</p>
      <p style="font-family:'Montserrat',sans-serif;font-size:8.5px;margin:0;color:${c.msgC};opacity:0.85;line-height:1.4;">${message}</p>
    </div>
    <button onclick="this.parentElement.remove()" style="background:none;border:none;cursor:pointer;font-size:9px;padding:5px 8px 0 0;align-self:flex-start;color:#fff;opacity:0.4;">✕</button>
    <div style="position:absolute;bottom:0;left:0;height:2px;background:${c.prog};animation:tProg 5s linear forwards;"></div>
  `;
  container.appendChild(toast);
  setTimeout(() => { toast.classList.add('hide'); setTimeout(() => toast.remove(), 300); }, 5000);
}

// ── SHOW DJANGO MESSAGES AS TOAST ON LOAD ──
window.addEventListener('load', () => {
  document.querySelectorAll('[id^="msg-"]').forEach(el => {
    const type = el.dataset.type.includes('success') ? 'success'
               : el.dataset.type.includes('error')   ? 'error'
               : 'warning';
    setTimeout(() => showToast(type, type === 'success' ? 'Done!' : 'Notice', el.textContent.trim()), 400);
  });
  // auto focus first OTP box
  document.getElementById('otp0').focus();
});