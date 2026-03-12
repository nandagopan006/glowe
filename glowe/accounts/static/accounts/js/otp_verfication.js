// ── Auto-advance OTP boxes ──
    const boxes = [
      document.getElementById('otp1'),
      document.getElementById('otp2'),
      document.getElementById('otp3'),
      document.getElementById('otp4'),
    ];
    const combined = document.getElementById('otp_combined');

    boxes.forEach((box, i) => {
      box.addEventListener('input', (e) => {
        // allow only numbers
        box.value = box.value.replace(/[^0-9]/g, '');
        if (box.value && i < 3) boxes[i + 1].focus();
        updateCombined();
      });

      box.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace' && !box.value && i > 0) {
          boxes[i - 1].focus();
          boxes[i - 1].value = '';
          updateCombined();
        }
      });

      // handle paste on first box
      box.addEventListener('paste', (e) => {
        e.preventDefault();
        const pasted = e.clipboardData.getData('text').replace(/[^0-9]/g, '').slice(0, 4);
        pasted.split('').forEach((char, idx) => {
          if (boxes[idx]) boxes[idx].value = char;
        });
        const next = Math.min(pasted.length, 3);
        boxes[next].focus();
        updateCombined();
      });
    });

    function updateCombined() {
      combined.value = boxes.map(b => b.value).join('');
    }

    // ── Countdown Timer ──
    let totalSeconds = 119; // 01:59
    const timerEl = document.getElementById('timer');
    const resendBtn = document.getElementById('resend-btn');

    resendBtn.disabled = true;

    const countdown = setInterval(() => {
      totalSeconds--;
      if (totalSeconds <= 0) {
        clearInterval(countdown);
        timerEl.textContent = '00:00 remaining';
        resendBtn.disabled = false;
        return;
      }
      const m = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
      const s = String(totalSeconds % 60).padStart(2, '0');
      timerEl.textContent = `${m}:${s} remaining`;
    }, 1000);

    // ── Resend Code ──
    function resendCode() {
      // Reset timer
      totalSeconds = 119;
      resendBtn.disabled = true;
      boxes.forEach(b => b.value = '');
      combined.value = '';
      boxes[0].focus();

      const newCountdown = setInterval(() => {
        totalSeconds--;
        if (totalSeconds <= 0) {
          clearInterval(newCountdown);
          timerEl.textContent = '00:00 remaining';
          resendBtn.disabled = false;
          return;
        }
        const m = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
        const s = String(totalSeconds % 60).padStart(2, '0');
        timerEl.textContent = `${m}:${s} remaining`;
      }, 1000);

      // POST to resend endpoint
      fetch('/resend-otp/', { method: 'POST', headers: { 'X-CSRFToken': getCookie('csrftoken') } });
    }

    function getCookie(name) {
      const val = `; ${document.cookie}`;
      const parts = val.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop().split(';').shift();
    }