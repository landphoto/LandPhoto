(function () {
  const sentinel = document.getElementById('infiniteSentinel');
  const grid = document.getElementById('feedGrid');
  if(!sentinel || !grid) return;

  const mode = sentinel.dataset.mode || 'home';
  const q = sentinel.dataset.q || '';
  const sort = sentinel.dataset.sort || 'new';
  const tag = sentinel.dataset.tag || '';

  let next = sentinel.dataset.next ? parseInt(sentinel.dataset.next,10) : null;
  let busy = false;

  function makeSkeletonRow(n=3){
    const frag = document.createDocumentFragment();
    for(let i=0;i<n;i++){
      const col = document.createElement('div');
      col.className = 'col-12 col-md-6 col-lg-4';
      col.innerHTML = '<div class="card land skel" style="height:360px;border-radius:20px"></div>';
      frag.appendChild(col);
    }
    return frag;
  }

  async function loadMore(){
    if(busy || !next) return; busy = true;
    grid.appendChild(makeSkeletonRow());
    try{
      const p = new URLSearchParams({ mode, page: next });
      if(mode==='search'){ p.set('q', q); p.set('sort', sort); }
      if(mode==='tag'){ p.set('tag', tag); }
      const r = await fetch(`/api/photos?${p.toString()}`);
      const d = await r.json();
      // احذف السكيليتون
      grid.querySelectorAll('.card.land.skel').forEach(e=>e.parentNode.remove());
      if(d.ok){
        const tmp = document.createElement('div'); tmp.innerHTML = d.html;
        while(tmp.firstChild){ grid.appendChild(tmp.firstChild); }
        // تفعيل Lazy/Lightbox للصور الجديدة
        if(window.lazyWebpInit) window.lazyWebpInit();
        next = d.has_more ? d.next : null;
      }
    }catch(e){
      // إزالة السكيليتون عند الخطأ
      grid.querySelectorAll('.card.land.skel').forEach(e=>e.parentNode.remove());
      next = null;
    }finally{ busy = false; }
  }

  const io = new IntersectionObserver((entries)=>{
    entries.forEach(e=>{
      if(e.isIntersecting) loadMore();
    });
  }, {rootMargin:'600px'});
  io.observe(sentinel);
})();