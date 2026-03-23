// ── TOAST ──
const T_CONFIGS = {
  success: { bg:'#1e3d2f', blobBg:'#172f24', iconBg:'radial-gradient(circle,#3aaa72,#1a6644)', icon:'✓', label:'#6ee7a8', titleC:'#f0fdf4', msgC:'#bbf7d0', prog:'#4ade80' },
  error:   { bg:'#3d1e1e', blobBg:'#2f1717', iconBg:'radial-gradient(circle,#e05050,#a82020)', icon:'!', label:'#fca5a5', titleC:'#fff1f2', msgC:'#fecaca', prog:'#f87171' },
  warning: { bg:'#3d2000', blobBg:'#2e1800', iconBg:'radial-gradient(circle,#f59e0b,#b45309)', icon:'!', label:'#fcd34d', titleC:'#fff8e1', msgC:'#fde68a', prog:'#f59e0b' },
};

function showToast(type, title, message) {
  const c = T_CONFIGS[type];
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.style.background = c.bg;
  toast.innerHTML = `
    <div style="width:40px;min-width:40px;align-self:stretch;display:flex;align-items:center;justify-content:center;overflow:hidden;background:${c.blobBg};">
      <div style="width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:#fff;background:${c.iconBg};">${c.icon}</div>
    </div>
    <div style="flex:1;padding:8px 4px 8px 8px;">
      <p style="font-family:'Montserrat',sans-serif;font-size:7px;font-weight:600;letter-spacing:0.2em;text-transform:uppercase;margin:0 0 1px;color:${c.label};">${type}</p>
      <p style="font-family:'Cormorant Garamond',serif;font-size:13px;font-weight:700;margin:0 0 1px;color:${c.titleC};line-height:1.2;">${title}</p>
      <p style="font-family:'Montserrat',sans-serif;font-size:8.5px;margin:0;color:${c.msgC};opacity:0.85;line-height:1.4;">${message}</p>
    </div>
    <button onclick="dismissToast(this.parentElement)" style="background:none;border:none;cursor:pointer;font-size:9px;padding:5px 8px 0 0;align-self:flex-start;color:#fff;opacity:0.4;">✕</button>
    <div style="position:absolute;bottom:0;left:0;height:2px;background:${c.prog};animation:tProg 5s linear forwards;"></div>
  `;
  container.appendChild(toast);
  toast._t = setTimeout(() => dismissToast(toast), 5000);
}

function dismissToast(t) {
  if (!t || t._d) return;
  t._d = true;
  clearTimeout(t._t);
  t.classList.add('hide');
  setTimeout(() => t.remove(), 300);
}

// ── PHOTO MODAL ──
function openPhotoModal() {
  const src = document.getElementById('avatarPreview').src;
  document.getElementById('modalPhoto').src = src;
  document.getElementById('photoModal').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closePhotoModal() {
  document.getElementById('photoModal').classList.remove('open');
  document.body.style.overflow = '';
}

function closeModalOutside(e) {
  if (e.target === document.getElementById('photoModal')) closePhotoModal();
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closePhotoModal();
});

// ── AVATAR CHANGE ──
function handleAvatarChange(input) {
  if (!input.files || !input.files[0]) return;
  const file = input.files[0];
  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
  if (!allowedTypes.includes(file.type)) {
    showToast('error', 'Invalid File', 'Please upload JPG, PNG or WEBP only.');
    input.value = '';
    return;
  }
  const reader = new FileReader();
  reader.onload = e => { document.getElementById('avatarPreview').src = e.target.result; };
  reader.readAsDataURL(file);
  document.getElementById('imageForm').submit();
}

// ── UNSAVED CHANGES BADGE ──
let isInitialLoad = true;

function markUnsaved() {
  if (isInitialLoad) return;
  const badge = document.getElementById('unsavedBadge');
  badge.classList.remove('hidden');
  badge.classList.add('flex');
}

document.querySelectorAll('.input-field, .phone-number-input').forEach(el => {
  el.addEventListener('input', markUnsaved);
});

// ── CHAR COUNTER ──
function updateCounter(inputId, counterId, max) {
  const len = document.getElementById(inputId).value.length;
  const el  = document.getElementById(counterId);
  el.textContent = `${len} / ${max}`;
  el.classList.toggle('warn', len >= max - 5);
}

// ── FORM SUBMIT WITH VALIDATION + LOADER ──
function handleSubmit(e) {
  e.preventDefault();

  const name          = document.getElementById('nameInput').value.trim();
  const email         = document.getElementById('emailInput').value.trim();
  const originalEmail = document.getElementById('originalEmail').value.trim();
  const isGoogleUser  = document.getElementById('isGoogleUser').value === 'true';
  const emailPattern  = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  let finalEmail = email;
  if (isGoogleUser && !finalEmail) {
    finalEmail = originalEmail;
  }

  if (!name || name.length < 4) {
    showToast('error', 'Name Required', 'Please enter your full name (at least 4 characters).');
    document.getElementById('nameInput').focus();
    return;
  }

  if (!name.replace(/ /g, '').match(/^[a-zA-Z]+$/)) {
    showToast('error', 'Invalid Name', 'Full name can only contain letters and spaces.');
    document.getElementById('nameInput').focus();
    return;
  }

  if (name.includes('  ')) {
    showToast('error', 'Invalid Name', 'Please remove double spaces from your name.');
    document.getElementById('nameInput').focus();
    return;
  }

  if (!isGoogleUser && !emailPattern.test(finalEmail)) {
    showToast('error', 'Invalid Email', 'Please enter a valid email address.');
    document.getElementById('emailInput').focus();
    return;
  }

  if (isGoogleUser && finalEmail !== originalEmail) {
    showToast('error', 'Email Locked', 'Google Sign-In users cannot change their email address.');
    document.getElementById('emailInput').focus();
    return;
  }

  const num = document.getElementById('phoneNumberInput').value.trim();
  if (num) {
    const cleanNum = num.replace(/\D/g, '');
    document.getElementById('full-phone-hidden').value = '+91' + cleanNum;
  }

  // ✅ MODERN LOADER
  const btn = document.getElementById('saveBtn');
  btn.classList.add('btn-loading');
  document.getElementById('saveBtnContent').innerHTML = `
    <span class="btn-spinner"></span>
    <span style="font-family:'Montserrat',sans-serif;font-size:10px;font-weight:600;letter-spacing:0.16em;text-transform:uppercase;">Saving...</span>
  `;

  document.getElementById('editForm').submit();
}

// ── INIT ON PAGE LOAD ──
window.addEventListener('load', () => {
  updateCounter('nameInput', 'nameCounter', 50);
  isInitialLoad = false;
  // ✅ Messages are handled by the inline <script> in edit_profile.html
});