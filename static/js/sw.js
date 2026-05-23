const CACHE_VERSION = 'gec-v1';
const STATIC_ASSETS = [
  '/static/css/design-system.css',
  '/static/css/base.css',
  '/static/css/style.css',
  '/static/vendor/bootstrap/bootstrap.min.css',
  '/static/vendor/fontawesome/css/all.min.css',
  '/static/vendor/jquery/jquery-3.7.1.min.js',
  '/static/vendor/bootstrap/bootstrap.bundle.min.js',
  '/static/js/app.js',
  '/static/js/base.js',
  '/static/img/icon-192.svg',
  '/static/favicon.svg',
];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE_VERSION).then(function (cache) {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (k) { return k !== CACHE_VERSION; })
            .map(function (k) { return caches.delete(k); })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function (e) {
  const url = new URL(e.request.url);

  // Ignore non-GET and cross-origin
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;

  // Static assets: cache first
  if (url.pathname.startsWith('/static/')) {
    e.respondWith(
      caches.match(e.request).then(function (cached) {
        if (cached) return cached;
        return fetch(e.request).then(function (resp) {
          if (resp && resp.status === 200) {
            const clone = resp.clone();
            caches.open(CACHE_VERSION).then(function (c) { c.put(e.request, clone); });
          }
          return resp;
        });
      })
    );
    return;
  }

  // HTML routes: network first, cache fallback
  e.respondWith(
    fetch(e.request).then(function (resp) {
      if (resp && resp.status === 200) {
        const clone = resp.clone();
        caches.open(CACHE_VERSION).then(function (c) { c.put(e.request, clone); });
      }
      return resp;
    }).catch(function () {
      return caches.match(e.request);
    })
  );
});
