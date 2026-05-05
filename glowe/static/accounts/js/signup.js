/* ── PASSWORD HELPERS ── */
function handleConfirmInput(input) {
  const eye = document.getElementById('confirm-eye');
  if (input.value.length > 0) {
    eye.classList.remove('hidden');
    eye.classList.add('flex');
  } else {
    eye.classList.add('hidden');
    eye.classList.remove('flex');
  }
}

function togglePwd(id, btn) {
  const input = document.getElementById(id);
  const isHidden = input.type === 'password';
  input.type = isHidden ? 'text' : 'password';
  btn.innerHTML = isHidden
    ? `<svg class="w-[16px] h-[16px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`
    : `<svg class="w-[16px] h-[16px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;
}

/* ── STEPS ── */
const STEPS = [
  { title: 'Validating details\u2026' },
  { title: 'Sending OTP\u2026'        },
  { title: 'Almost there\u2026'       },
];
const STEP_MS = 1500;

/* ── ON PAGE LOAD ── */
document.addEventListener('DOMContentLoaded', function () {

  var form = document.getElementById('signup-form');
  if (!form) return;

  form.addEventListener('submit', function () {
    // NO e.preventDefault() — form submits normally to Django ✅

    var btn    = document.getElementById('submit-btn');
    var label  = document.getElementById('btn-label');
    var arrow  = document.getElementById('btn-arrow');
    var loader = document.getElementById('btn-loader');

    // stop if errors already on page
    var hasPageErrors = document.querySelector('.text-red-500') !== null;
    if (hasPageErrors) return;

    // show loader
    btn.disabled         = true;
    arrow.style.display  = 'none';
    label.textContent    = STEPS[0].title;
    loader.style.display = 'flex';

    // cycle through steps while form submits
    var step = 1;
    setInterval(function () {
      if (step >= STEPS.length) return;
      label.textContent = STEPS[step].title;
      step++;
    }, STEP_MS);

    // form submits normally to Django ✅
    // no fetch — no CSRF problem ✅
  });
});