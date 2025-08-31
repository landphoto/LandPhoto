// comments.js — يمنع ريفرش، يفعّل الفاليديشن، يضيف التعليق فوراً، وإعجاب التعليق
window.addEventListener('DOMContentLoaded', () => {
  // منع أي زر إرسال داخل النموذج من تسبب التنقل للأعلى
  document.addEventListener('click', (e) => {
    if (e.target.closest('.comment-form .send-btn')) e.preventDefault();
  });

  // إرسال تعليق
  document.addEventListener('submit', async (e) => {
    const form = e.target;
    if (!form.matches('.comment-form')) return;
    e.preventDefault();

    const pid   = form.getAttribute('data-pid');
    const input = form.querySelector('input[name="content"]');
    const list  = form.closest('.glass-comments').querySelector('[data-comments-list]');

    // فاليديشن Bootstrap
    if (!input.value.trim()) {
      form.classList.add('was-validated');
      input.classList.add('is-invalid');
      input.focus();
      return false;
    } else {
      input.classList.remove('is-invalid');
    }

    try {
      const resp = await fetch(`/post/${pid}/comment`, {
        method: 'POST',
        headers: {'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8'},
        body: new URLSearchParams({ content: input.value.trim() })
      });
      const data = await resp.json();
      if (!data.ok) throw new Error(data.msg || 'تعذر إرسال التعليق');

      // أضف التعليق أعلى القائمة
      const c = data.comment;
      const el = document.createElement('div');
      el.className = 'd-flex align-items-start gap-2 comment-item p-2 rounded-3';
      el.innerHTML = `
        <a href="/u/${c.user.username || ''}" class="text-decoration-none">
          <img src="${c.user.avatar}" class="avatar-xs" alt="">
        </a>
        <div class="flex-grow-1">
          <div class="d-flex align-items-center justify-content-between">
            <a href="/u/${c.user.username || ''}" class="fw-semibold small text-warning text-decoration-none">
              ${c.user.display_name || c.user.username}
            </a>
            <small class="time-badge">الآن</small>
          </div>
          <div class="d-flex align-items-center justify-content-between mt-1">
            <div class="comment-text me-2"></div>
            <button class="c-like" type="button" data-cid="${c.id}">
              <i class="bi bi-heart"></i> <span class="small ms-1" data-like-count>0</span>
            </button>
          </div>
        </div>`;
      el.querySelector('.comment-text').textContent = c.content;
      list.prepend(el);

      // تفريغ الحقل
      input.value = '';
      form.classList.remove('was-validated');
      input.classList.remove('is-invalid');
    } catch (err) {
      console.error(err);
      const tip = form.querySelector('.glass-tip');
      tip.textContent = 'حدث خطأ، حاول مرة أخرى';
      tip.classList.add('show');
      setTimeout(() => {
        tip.classList.remove('show');
        tip.textContent = 'يرجى ملء هذا الحقل.';
      }, 1800);
    }
    return false;
  });

  // إعجاب/إلغاء إعجاب تعليق
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.c-like');
    if (!btn) return;
    e.preventDefault();

    const cid = btn.getAttribute('data-cid');
    const icon = btn.querySelector('i');
    const counter = btn.querySelector('[data-like-count]');

    try {
      const resp = await fetch(`/comment/${cid}/like`, { method: 'POST' });
      const data = await resp.json();
      if (!data.ok) throw new Error('err');

      counter.textContent = data.count;
      if (data.on) {
        icon.classList.remove('bi-heart');
        icon.classList.add('bi-heart-fill', 'text-danger');
      } else {
        icon.classList.remove('bi-heart-fill', 'text-danger');
        icon.classList.add('bi-heart');
      }
    } catch (err) {
      console.error(err);
    }
  });
});

// تحذير زجاجي + إرسال تعليق + لا تصعد الصفحة للأعلى
window.addEventListener('DOMContentLoaded', () => {

  // إخفاء التحذير عند الكتابة
  document.addEventListener('input', (e) => {
    const form = e.target.closest('.comment-form');
    if (!form) return;
    const tip = form.querySelector('[data-tip]');
    if (tip) tip.classList.remove('show');
    e.target.classList.remove('is-invalid');
    form.classList.remove('was-validated');
  });

  // إرسال التعليق
  document.addEventListener('submit', async (e) => {
    const form = e.target;
    if (!form.matches('.comment-form')) return;
    e.preventDefault(); // لا تقفز للأعلى

    const pid   = form.getAttribute('data-pid');
    const input = form.querySelector('input[name="content"]');
    const tip   = form.querySelector('[data-tip]');
    const wrap  = form.querySelector('.position-relative');

    // تحقّق من الفراغ
    if (!input.value.trim()) {
      form.classList.add('was-validated');
      input.classList.add('is-invalid');
      if (tip) {
        tip.textContent = 'يرجى ملء هذا الحقل.';
        tip.classList.add('show');
        // أخفِها بعد ثانية ونص (اختياري)
        setTimeout(() => tip.classList.remove('show'), 1600);
      }
      input.focus();
      return false;
    }

    // طلب الإرسال العادي
    try {
      const resp = await fetch(`/post/${pid}/comment`, {
        method: 'POST',
        headers: {'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8'},
        body: new URLSearchParams({ content: input.value.trim() })
      });
      const data = await resp.json();
      if (!data.ok) throw new Error(data.msg || 'تعذر إرسال التعليق');

      // أضِف التعليق أعلى القائمة
      const list = form.closest('.glass-comments')?.querySelector('[data-comments-list]');
      if (list) {
        const c = data.comment;
        const el = document.createElement('div');
        el.className = 'd-flex align-items-start gap-2 comment-item p-2 rounded-3';
        el.innerHTML = `
          <a href="/u/${c.user.username || ''}" class="text-decoration-none">
            <img src="${c.user.avatar}" class="avatar-xs" alt="">
          </a>
          <div class="flex-grow-1">
            <div class="d-flex align-items-center justify-content-between">
              <a href="/u/${c.user.username || ''}" class="fw-semibold small text-warning text-decoration-none">
                ${c.user.display_name || c.user.username}
              </a>
              <small class="time-badge">الآن</small>
            </div>
            <div class="d-flex align-items-center justify-content-between mt-1">
              <div class="comment-text me-2"></div>
              <button class="c-like" type="button" data-cid="${c.id}">
                <i class="bi bi-heart"></i> <span class="small ms-1" data-like-count>0</span>
              </button>
            </div>
          </div>`;
        el.querySelector('.comment-text').textContent = c.content;
        list.prepend(el);
      }

      // تنظيف الحقل
      input.value = '';
      input.classList.remove('is-invalid');
      form.classList.remove('was-validated');
      if (tip) tip.classList.remove('show');

    } catch (err) {
      console.error(err);
      if (tip) {
        tip.textContent = 'حدث خطأ، حاول ثانيةً';
        tip.classList.add('show');
        setTimeout(() => { tip.classList.remove('show'); tip.textContent = 'يرجى ملء هذا الحقل.'; }, 2000);
      }
    }
    return false;
  });

  // إعجاب تعليق (لو ما كان عندك مسبقًا)
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.c-like');
    if (!btn) return;
    e.preventDefault();
    const cid = btn.getAttribute('data-cid');
    const icon = btn.querySelector('i');
    const counter = btn.querySelector('[data-like-count]');
    try {
      const resp = await fetch(`/comment/${cid}/like`, { method: 'POST' });
      const data = await resp.json();
      if (!data.ok) throw 0;
      counter.textContent = data.count;
      if (data.on) { icon.classList.replace('bi-heart', 'bi-heart-fill'); icon.classList.add('text-danger'); }
      else { icon.classList.replace('bi-heart-fill', 'bi-heart'); icon.classList.remove('text-danger'); }
    } catch { /* تجاهل */ }
  });
});

  // إعجاب التعليق كما هو…
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.c-like');
    if (!btn) return;
    e.preventDefault();

    const cid = btn.getAttribute('data-cid');
    const icon = btn.querySelector('i');
    const counter = btn.querySelector('[data-like-count]');

    try {
      const resp = await fetch(`/comment/${cid}/like`, { method: 'POST' });
      const data = await resp.json();
      if (!data.ok) throw new Error('err');

      counter.textContent = data.count;
      if (data.on) {
        icon.classList.remove('bi-heart');
        icon.classList.add('bi-heart-fill', 'text-danger');
      } else {
        icon.classList.remove('bi-heart-fill', 'text-danger');
        icon.classList.add('bi-heart');
      }
    } catch (err) { console.error(err); }
  });
});