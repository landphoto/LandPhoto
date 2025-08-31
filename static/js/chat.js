(function () {
  const form = document.getElementById('chatForm');
  const input = document.getElementById('chatInput');
  const body = document.getElementById('chatBody');
  if (!form || !input || !body) return;

  const scrollBottom = () => { body.scrollTop = body.scrollHeight; };
  scrollBottom();

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!input.value.trim()) {
      // تنبيه حلو Bootstrap 5 (Toast/Alert)
      const al = document.createElement('div');
      al.className = 'alert alert-warning glass mt-2';
      al.innerHTML = '<i class="bi bi-exclamation-triangle"></i> يرجى كتابة رسالة.';
      form.parentElement.insertBefore(al, form);
      setTimeout(() => al.remove(), 1600);
      return;
    }

    const fd = new FormData(form);
    const url = (window.LP_CHAT && window.LP_CHAT.sendUrl) || form.action;

    try {
      const res = await fetch(url, { method: 'POST', body: fd });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.msg || 'خطأ في الإرسال');
      }
      const j = await res.json();

      // أضف الفقاعة فورًا
      const wrap = document.createElement('div');
      wrap.className = 'chat-row me';
      wrap.innerHTML = `
        <div class="chat-bubble glass me">
          ${escapeHtml(input.value.trim())}
          <div class="chat-time small">الآن</div>
        </div>`;
      body.appendChild(wrap);
      input.value = '';
      scrollBottom();
    } catch (err) {
      const al = document.createElement('div');
      al.className = 'alert alert-danger glass mt-2';
      al.textContent = err.message || 'تعذر الإرسال';
      form.parentElement.insertBefore(al, form);
      setTimeout(() => al.remove(), 1800);
    }
  });

  function escapeHtml(str){
    return str.replace(/[&<>"']/g, s => (
      {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]
    ));
  }
})();