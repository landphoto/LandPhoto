/* LandPhoto basic SW: cache shell + network-first for pages */
const CACHE = 'landphoto-v1';
const ASSETS = [
  '/', 
  '/static/pwa/manifest.webmanifest'
  // تقدر تضيف ملفات CSS/JS الأساسية لو تحب
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // لا نكاشف APIs والملفات الكبيرة/الديناميكية
  if (url.pathname.startsWith('/api/')) return;
  if (url.pathname.startsWith('/static/chat_uploads')) return;

  // صفحات: شبكة أولاً مع تخزين النتيجة
  e.respondWith(
    fetch(e.request).then(resp => {
      const copy = resp.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy)).catch(()=>{});
      return resp;
    }).catch(() => caches.match(e.request))
  );
});