// فتح الصور بنوافذ – ضع أي لايت بوكس لاحقاً
document.addEventListener('click', e=>{
  const a = e.target.closest('a.lightbox'); if(!a) return;
  e.preventDefault(); window.open(a.href, '_blank');
});