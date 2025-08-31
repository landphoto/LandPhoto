// Helper to POST form data
async function post(url, data) {
  const resp = await fetch(url, { method:'POST', body: data, credentials:'same-origin' });
  return resp.json();
}

document.addEventListener('click', async (e) => {
  // Like
  const likeBtn = e.target.closest('.like-btn');
  if (likeBtn) {
    if (!document.body.dataset.auth && likeBtn.dataset.mustauth) return;
    const pid = likeBtn.dataset.pid;
    const data = new FormData();
    const res = await post(`/post/${pid}/like`, data);
    if (res.ok) {
      const icon = likeBtn.querySelector('i');
      const cnt  = likeBtn.querySelector('.like-count');
      if (res.liked) icon.className = 'bi bi-heart-fill text-danger';
      else icon.className = 'bi bi-heart';
      cnt.textContent = res.count;
    }
  }

  // Bookmark
  const bm = e.target.closest('.bookmark-btn');
  if (bm) {
    const pid = bm.dataset.pid;
    const res = await post(`/post/${pid}/bookmark`, new FormData());
    if (res.ok) {
      const i = bm.querySelector('i');
      i.className = res.saved ? 'bi bi-bookmark-check-fill text-warning' : 'bi bi-bookmark';
    }
  }

  // Follow toggle
  const followBtn = e.target.closest('.follow-btn');
  if (followBtn) {
    const u = followBtn.dataset.username;
    const res = await post(`/follow/${u}`, new FormData());
    if (res.ok) {
      followBtn.innerHTML = res.on ? '<i class="bi bi-person-check"></i> تتابع' :
                                     '<i class="bi bi-person-plus"></i> متابعة';
    }
  }
});

// Comment submit
document.addEventListener('submit', async (e) => {
  const form = e.target.closest('.comment-form');
  if (!form) return;
  e.preventDefault();
  const input = form.querySelector('input');
  const pid = form.dataset.pid;
  const fd = new FormData();
  fd.append('content', input.value);
  const res = await post(`/post/${pid}/comment`, fd);
  if (res.ok) {
    input.value = '';
    const wrap = form.parentElement.querySelector('.comments');
    const div = document.createElement('div');
    div.className = 'mt-2 glass p-2 rounded-3';
    div.innerHTML = `<img src="${res.comment.user.avatar}" class="avatar-xs ring-gold shadow-gold me-2">
                     <b class="small">${res.comment.user.display_name}</b>
                     <div class="small mt-1">${res.comment.content}</div>`;
    wrap.prepend(div);
    form.parentElement.querySelector('.comment-count').textContent = res.count;
  }
});

// إرسال تعليق بزجاجية + تلميح تحقق
document.addEventListener('submit', async (e) => {
  const form = e.target.closest('.comment-form');
  if (!form) return;

  e.preventDefault();
  const pid = form.getAttribute('data-pid');
  const input = form.querySelector('input[name="content"]');

  // تحقق بسيط بديل فقاعة المتصفح
  if (!input.value.trim()) {
    input.classList.add('is-invalid');
    setTimeout(() => input.classList.remove('is-invalid'), 1800);
    return;
  }

  // إرسال
  const body = new FormData();
  body.append('content', input.value.trim());

  try {
    const res = await fetch(`/post/${pid}/comment`, { method: 'POST', body });
    const data = await res.json();
    if (!data.ok) throw new Error(data.msg || 'خطأ');

    // أضف التعليق مباشرة أعلى القائمة
    const list = form.parentElement.querySelector('.vstack') || (() => {
      const v = document.createElement('div');
      v.className = 'vstack gap-2 mb-3';
      form.parentElement.insertBefore(v, form);
      return v;
    })();

    const c = data.comment;
    const wrapper = document.createElement('div');
    wrapper.className = 'comment-item p-2 rounded-3 d-flex align-items-start gap-2';
    wrapper.innerHTML = `
      <img src="${c.user.avatar}" class="avatar-xs flex-shrink-0" alt="">
      <div class="flex-grow-1">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <a href="/u/${c.user.username || c.user.display_name}" class="comment-user text-warning fw-semibold text-decoration-none">
            ${c.user.display_name || c.user.username}
          </a>
          <small class="time-badge">${c.created}</small>
        </div>
        <div class="comment-text"></div>
      </div>`;
    wrapper.querySelector('.comment-text').textContent = c.content;
    list.prepend(wrapper);

    input.value = '';
  } catch (err) {
    console.error(err);
    input.classList.add('is-invalid');
    form.querySelector('.glass-tip').textContent = 'تعذر الإرسال، حاول مجددًا.';
    setTimeout(() => {
      input.classList.remove('is-invalid');
      form.querySelector('.glass-tip').textContent = 'يُرجى ملء هذا الحقل.';
    }, 2000);
  }
});