/* ===== موجوداتك السابقة إن وُجدت يمكن إبقاؤها هنا ===== */

/* ===== Navbar glow pulse on open/close ===== */
(function(){
  const toggler = document.getElementById('menuToggle');
  const nav = document.getElementById('nav');
  if(!toggler || !nav) return;
  function pulse(){
    toggler.classList.add('glow-pulse');
    setTimeout(()=>toggler.classList.remove('glow-pulse'), 900);
  }
  nav.addEventListener('show.bs.collapse', pulse);
  nav.addEventListener('hide.bs.collapse', pulse);
})();

/* ===== Comments logic (relative time + like + send) ===== */
(function(){
  // Relative time in Arabic
  const rtf = new Intl.RelativeTimeFormat('ar', {numeric:'auto'});
  function timeAgoFrom(date){
    const now = Date.now();
    const diff = (new Date(date)).getTime() - now;
    const sec = Math.round(diff/1000);
    const mins = Math.round(sec/60);
    const hours = Math.round(mins/60);
    const days = Math.round(hours/24);
    if (Math.abs(sec) < 60)   return rtf.format(sec, 'second');
    if (Math.abs(mins) < 60)  return rtf.format(mins, 'minute');
    if (Math.abs(hours) < 24) return rtf.format(hours, 'hour');
    return rtf.format(days, 'day');
  }
  function refreshTimes(){
    document.querySelectorAll('.time-badge[data-ts]').forEach(el=>{
      el.textContent = timeAgoFrom(el.dataset.ts);
    });
  }
  refreshTimes(); setInterval(refreshTimes, 60000);

  // Like a comment
  document.addEventListener('click', async (e)=>{
    const btn = e.target.closest('.heart-btn');
    if(!btn) return;
    const cid = btn.dataset.cid;
    try{
      const res = await fetch(`/comments/${encodeURIComponent(cid)}/like`, {method:'POST'});
      const data = await res.json();
      if(data && data.ok){
        const icon = btn.querySelector('i');
        btn.classList.toggle('on', data.liked);
        icon.className = 'bi ' + (data.liked ? 'bi-heart-fill' : 'bi-heart');
        const countEl = document.getElementById(`cLikes-${cid}`);
        if(countEl) countEl.textContent = data.likes;
      }
    }catch(err){}
  });

  // Submit comment
  document.addEventListener('submit', async (e)=>{
    const form = e.target.closest('.comment-form');
    if(!form) return;
    e.preventDefault();
    const pid = form.dataset.pid;
    const input = form.querySelector('input[name="text"]');
    const text = (input.value || '').trim();
    if(!text) return;

    const btn = form.querySelector('.send-btn');
    btn.disabled = true;
    try{
      const res = await fetch(`/posts/${encodeURIComponent(pid)}/comments`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({text})
      });
      const data = await res.json();
      if(data && data.ok){
        const box = document.getElementById(`comments-${pid}`);
        const el = document.createElement('div');
        el.className = 'comment-item d-flex gap-2 align-items-start rounded-3 p-2';
        el.innerHTML = `
          <img src="${data.author_avatar}" class="avatar-xs" alt="${data.author_name}">
          <div class="flex-grow-1">
            <div class="d-flex align-items-center gap-2 mb-1">
              <strong class="small text-contrast">${data.author_name}</strong>
              <span class="time-badge" data-ts="${data.created_at_iso}">الآن</span>
            </div>
            <div class="comment-text small"></div>
            <div class="d-flex align-items-center gap-2 mt-1">
              <button class="heart-btn" data-cid="${data.id}" aria-label="أعجبني"><i class="bi bi-heart"></i></button>
              <span class="like-count small" id="cLikes-${data.id}">0</span>
            </div>
          </div>`;
        el.querySelector('.comment-text').textContent = data.text;
        box.appendChild(el);
        input.value = '';
        refreshTimes();
      }
    }catch(err){}
    btn.disabled = false;
  });
})();