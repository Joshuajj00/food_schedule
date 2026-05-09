// PWA Service Worker — 오프라인 캐싱
const CACHE_NAME = 'diet-assistant-v2';

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll([
                '/',
                '/static/index.html',
                '/static/manifest.json',
            ]);
        })
    );
});

self.addEventListener('fetch', (event) => {
    // API 요청은 캐시하지 않음
    if (event.request.url.includes('/api/')) {
        return;
    }
    event.respondWith(
        caches.match(event.request).then((cached) => {
            return cached || fetch(event.request);
        })
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
            );
        })
    );
});
