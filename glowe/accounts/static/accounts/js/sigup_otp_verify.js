const boxes      = document.querySelectorAll('.otp-input');
    const hiddenInput = document.getElementById('otp-hidden');
    const form       = document.getElementById('otp-form');
    const timerEl    = document.getElementById('timer');
    const resendBtn  = document.getElementById('resend-btn');

    // ── OTP BOX BEHAVIOUR ──

    boxes.forEach((box, i) => {

      // only allow numbers, move to next box on input
      box.addEventListener('input', () => {
        box.value = box.value.replace(/[^0-9]/g, '');

        if (box.value) {
          box.classList.add('filled');
          box.classList.remove('error-box');
          // move focus to next box
          if (i < boxes.length - 1) boxes[i + 1].focus();
        } else {
          box.classList.remove('filled');
        }
      });

      // backspace goes to previous box
      box.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace' && !box.value && i > 0) {
          boxes[i - 1].focus();
          boxes[i - 1].value = '';
          boxes[i - 1].classList.remove('filled');
        }
      });

      // paste full otp at once like "4829"
      box.addEventListener('paste', (e) => {
        e.preventDefault();
        const pasted = e.clipboardData.getData('text').replace(/[^0-9]/g, '');
        boxes.forEach((b, idx) => {
          b.value = pasted[idx] || '';
          if (b.value) {
            b.classList.add('filled');
          } else {
            b.classList.remove('filled');
          }
        });
        // focus last filled box
        const lastIdx = Math.min(pasted.length, boxes.length) - 1;
        if (lastIdx >= 0) boxes[lastIdx].focus();
      });
    });

    // ── FORM SUBMIT ──

    form.addEventListener('submit', (e) => {
      const otp = Array.from(boxes).map(b => b.value).join('');

      // if not all 4 boxes filled — shake and stop submit
      if (otp.length < 4) {
        e.preventDefault();
        boxes.forEach(b => {
          b.classList.add('error-box', 'shake');
          setTimeout(() => b.classList.remove('shake'), 400);
        });
        return;
      }

      // pass all 4 digits as one value to django
      hiddenInput.value = otp;
    });

    // ── COUNTDOWN TIMER ──

    let seconds = 60;

    const countdown = setInterval(() => {
      seconds--;

      const mins = String(Math.floor(seconds / 60)).padStart(2, '0');
      const secs = String(seconds % 60).padStart(2, '0');
      timerEl.textContent = `${mins}:${secs} remaining`;

      // when timer reaches 0 — enable resend button
      if (seconds <= 0) {
        clearInterval(countdown);
        timerEl.textContent = 'Code expired. Please resend.';
        resendBtn.classList.remove('pointer-events-none', 'opacity-40');
      }
    }, 1000);

    // focus first box on page load
    boxes[0].focus();