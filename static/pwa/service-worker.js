// عدّل الرقم كل تحديث لإجبار تحديث الكاش
const CACHE_VERSION = 'v3';
const CACHE_NAME = `landphoto-${CACHE_VERSION}`;
const ASSETS = [
  '/', 
  '/static/css/style.css', // عدّل حسب ملفاتك الفعلية
  '/static/js/app.js'      // عدّل حسب ملفاتك الفعلية
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k.startsWith('landphoto-') && k !== CACHE_NAME).map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  e.respondWith(
    caches.match(req).then(cached => cached || fetch(req))
  );
});