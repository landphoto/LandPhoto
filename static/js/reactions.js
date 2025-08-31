// كل شيء متوافق مع app.py الذي أرسلته:
document.addEventListener('click', async (e)=>{
  const likeBtn = e.target.closest('[data-like-post]');
  const saveBtn = e.target.closest('[data-bookmark-post]');
  const shareBtn = e.target.closest('[data-share]');
  const emojiBtn = e.target.closest('.emoji-btn');

  // إعجاب
  if(likeBtn){
    const id = likeBtn.getAttribute('data-like-post');
    likeBtn.disabled = true;
    try{
      const r = await fetch(`/post/${id}/like`, {method:'POST'});
      if(r.ok){
        const icon = likeBtn.querySelector('i');
        icon.classList.toggle('bi-heart');
        icon.classList.toggle('bi-hearts-fill');
      }
    }finally{ likeBtn.disabled=false; }
  }

  // حفظ
  if(saveBtn){
    const id = saveBtn.getAttribute('data-bookmark-post');
    saveBtn.disabled = true;
    try{
      const r = await fetch(`/post/${id}/bookmark`, {method:'POST'});
      if(r.ok){
        const i = saveBtn.querySelector('i');
        i.classList.toggle('bi-bookmark');
        i.classList.toggle('bi-bookmark-fill');
      }
    }finally{ saveBtn.disabled=false; }
  }

  // مشاركة
  if(shareBtn){
    const id = shareBtn.getAttribute('data-post-id');
    const url = `${location.origin}/p/${id}`;
    try{
      if(navigator.share){ await navigator.share({title:'منشور لند فوتو', url}); }
      else{ await navigator.clipboard.writeText(url); shareBtn.classList.add('active'); setTimeout(()=>shareBtn.classList.remove('active'),800); }
    }catch{}
  }

  // ردة فعل تعليق
  if(emojiBtn){
    const bar = emojiBtn.closest('.emoji-bar');
    const cid = bar.getAttribute('data-comment-id');
    const emoji = emojiBtn.getAttribute('data-emoji');
    const fd = new FormData(); fd.append('emoji', emoji);
    emojiBtn.disabled = true;
    try{
      const r = await fetch(`/comment/${cid}/react`, {method:'POST', body:fd});
      if(r.ok){ location.reload(); }
    }finally{ emojiBtn.disabled=false; }
  }
});

// إرسال التعليق عبر نفس مسار app.py
document.addEventListener('submit', async (e)=>{
  const form = e.target.closest('form.js-comment-form');
  if(!form) return;
  e.preventDefault();
  const url = form.action;
  const fd  = new FormData(form);
  try{
    const r = await fetch(url, {method:'POST', body:fd});
    if(r.ok){ location.reload(); }
  }catch{}
});