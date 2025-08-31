(function () {
  function supportsWebp() {
    try {
      return document.createElement('canvas').toDataURL('image/webp').indexOf('data:image/webp') === 0;
    } catch(e){ return false; }
  }
  const webp = supportsWebp();
  const io = new IntersectionObserver((entries, obs)=>{
    entries.forEach(e=>{
      if(!e.isIntersecting) return;
      const el = e.target;
      const thumb = el.getAttribute('data-src');
      const full = el.getAttribute('data-full');
      if(!thumb){ obs.unobserve(el); return; }
      // حدد مصدر العرض المبدئي (الثمبنيل)
      el.src = thumb;
      // لو فيه webp صالحة استبدل لاحقاً
      if (webp && full) {
        // لو الملف اسمه xxx.jpg => ابحث xxx_md.webp كنسخة وسط
        const md = full.replace(/(\.\w+)$/i, '_md.webp');
        const img = new Image();
        img.onload = ()=> { el.src = md; };
        img.src = md;
      }
      obs.unobserve(el);
    });
  }, {rootMargin: '300px'});

  document.querySelectorAll('img.lp-img').forEach(im=>io.observe(im));
})();