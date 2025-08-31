(function(){
  const menu = document.createElement('div');
  menu.style.position='absolute'; menu.style.zIndex='1500';
  menu.style.background='rgba(20,20,28,.95)'; menu.style.border='1px solid #ffffff22';
  menu.style.backdropFilter='blur(8px)'; menu.style.borderRadius='12px';
  menu.style.padding='.25rem'; menu.style.display='none'; menu.style.minWidth='160px';
  document.body.appendChild(menu);

  let anchor = null, type = null; // '@' أو '#'
  function hide(){ menu.style.display='none'; anchor=null; type=null; }
  function place(el){
    const r = el.getBoundingClientRect();
    menu.style.top = (window.scrollY + r.bottom + 6) + 'px';
    menu.style.left= (window.scrollX + r.left) + 'px';
  }
  function build(list, input){
    menu.innerHTML='';
    list.forEach(v=>{
      const btn = document.createElement('button');
      btn.type='button';
      btn.style.display='block';
      btn.style.width='100%';
      btn.style.textAlign='start';
      btn.style.background='transparent';
      btn.style.border='0';
      btn.style.padding='.35rem .5rem';
      btn.style.color='#fff';
      btn.textContent = (type==='@'?'@':'#') + v;
      btn.addEventListener('click', ()=>{
        const cur = input.value;
        const caret = input.selectionStart;
        // استبدال آخر كلمة بالاختيار
        const before = cur.slice(0, caret).replace(/([#@])[\w\p{L}\p{N}_-]*$/u, (m, sym)=> sym + v + ' ');
        input.value = before + cur.slice(caret);
        hide(); input.focus();
      });
      menu.appendChild(btn);
    });
    if(list.length===0){
      const em = document.createElement('div');
      em.style.color='#cfcfd8cc'; em.style.padding='.35rem .5rem';
      em.textContent = 'لا اقتراحات';
      menu.appendChild(em);
    }
  }

  async function suggest(prefix){
    if(type==='@'){
      const r = await fetch(`/api/users/suggest?q=${encodeURIComponent(prefix)}`); const d=await r.json();
      return d.items||[];
    }else{
      const r = await fetch(`/api/tags/top`); const d=await r.json();
      const arr = (d.tags||[]).filter(t=>t.startsWith(prefix)).slice(0,8);
      return arr;
    }
  }

  function onInput(e){
    const input = e.target;
    if(!input.classList.contains('comment-input') && input.name!=='caption') return;
    const caret = input.selectionStart;
    const upto = input.value.slice(0, caret);
    const m = upto.match(/([#@])([\w\p{L}\p{N}_-]{1,20})$/u);
    if(!m){ hide(); return; }
    type = m[1]; const pref = m[2] || '';
    place(input); menu.style.display='block';
    suggest(pref).then(list=> build(list, input));
  }

  document.addEventListener('input', onInput);
  document.addEventListener('click', (e)=>{ if(!menu.contains(e.target)) hide(); });
  window.addEventListener('scroll', ()=>{ if(anchor) place(anchor); }, true);
})();