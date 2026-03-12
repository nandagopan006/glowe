// ── GET ELEMENTS ──
const inputs      = document.querySelectorAll('.otp-input');
const hiddenInput = document.getElementById('otp-hidden');
const otpBoxes    = document.getElementById('otp-boxes');
const resendBtn   = document.getElementById('resend-btn');
const timerEl     = document.getElementById('timer');

// ── TOAST ──
let toastTimer = null;

function showToast(message, type) {
  const toast     = document.getElementById('toast');
  const toastMsg  = document.getElementById('toast-msg');
  const toastIcon = document.getElementById('toast-icon');
  const iconWrap  = document.getElementById('toast-icon-wrap');

  // clear existing timer
  if (toastTimer) clearTimeout(toastTimer);

  // set message
  toastMsg.textContent = message;

  // set style based on type
  if (type === 'error') {
    toastIcon.textContent     = '✕';
    toast.style.background    = 'rgba(127,29,29,0.92)';
    iconWrap.style.background = 'rgba(255,255,255,0.15)';
  } else if (type === 'warning') {
    toastIcon.textContent     = '⏱';
    toast.style.background    = 'rgba(42,31,20,0.92)';
    iconWrap.style.background = 'rgba(255,255,255,0.15)';
  } else if (type === 'success') {
    toastIcon.textContent     = '✓';
    toast.style.background    = 'rgba(20,83,45,0.92)';
    iconWrap.style.background = 'rgba(255,255,255,0.15)';
  }

  // show — slide down from top
  toast.style.transform     = 'translateX(-50%) translateY(0)';
  toast.style.opacity       = '1';
  toast.style.pointerEvents = 'auto';

  // auto hide after 3.5 seconds
  toastTimer = setTimeout(() => hideToast(), 3500);
}

function hideToast() {
  const toast = document.getElementById('toast');
  toast.style.transform     = 'translateX(-50%) translateY(-80px)';
  toast.style.opacity       = '0';
  toast.style.pointerEvents = 'none';
}

// ── TYPING IN BOX ──
inputs.forEach((input, index) => {

  // when user types
  input.addEventListener('input', () => {
    // only allow numbers
    input.value = input.value.replace(/[^0-9]/g, '');

    if (input.value) {
      input.classList.add('filled');
      // jump to next box
      if (index < inputs.length - 1) {
        inputs[index + 1].focus();
      }
    } else {
      input.classList.remove('filled');
    }

    // combine all 4 boxes into hidden input
    hiddenInput.value = Array.from(inputs).map(i => i.value).join('');
  });

  // backspace → go to previous box
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace' && !input.value && index > 0) {
      inputs[index - 1].focus();
      inputs[index - 1].value = '';
      inputs[index - 1].classList.remove('filled');
    }
  });

  // paste support
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

// ── SHAKE + TOAST ON WRONG OTP ──
const errorEl = document.querySelector('.text-red-500');
if (errorEl) {
  // shake boxes
  otpBoxes.classList.add('shake');
  inputs.forEach(i => i.classList.add('error-box'));
  setTimeout(() => otpBoxes.classList.remove('shake'), 500);

  // show error toast
  showToast(errorEl.textContent.trim(), 'error');
}

// ── TIMER ──
let seconds = typeof SECONDS_LEFT !== 'undefined' ? SECONDS_LEFT : 60;

// update display immediately on load
const initM = String(Math.floor(seconds / 60)).padStart(2, '0');
const initS = String(seconds % 60).padStart(2, '0');
timerEl.textContent = `${initM}:${initS} remaining`;

// already expired on page load
if (seconds <= 0) {
  timerEl.textContent = 'OTP expired';
  resendBtn.classList.remove('pointer-events-none', 'opacity-40');
  showToast('Your OTP has expired. Please request a new one.', 'warning');
}

// start countdown
const timerInterval = setInterval(() => {
  seconds--;

  const m = String(Math.floor(seconds / 60)).padStart(2, '0');
  const s = String(seconds % 60).padStart(2, '0');
  timerEl.textContent = `${m}:${s} remaining`;

  // timer hits 0
  if (seconds <= 0) {
    clearInterval(timerInterval);
    timerEl.textContent = 'OTP expired';

    // unlock resend button
    resendBtn.classList.remove('pointer-events-none', 'opacity-40');

    // show expiry toast
    showToast('Your OTP has expired. Please request a new one.', 'warning');
  }

}, 1000);

// ── RESEND CLICK ──
resendBtn.addEventListener('click', () => {
  resendBtn.classList.add('pointer-events-none', 'opacity-40');
});