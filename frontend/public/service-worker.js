/* WeatherFit 서비스워커 (수동 작성)
 *
 * 전략
 *  - 같은 출처 정적 자산(JS/CSS/폰트/이미지): Stale-While-Revalidate
 *    (해시 파일명이라 새 빌드는 새 파일명 → 오래된 캐시가 남아도 안전)
 *  - 페이지 내비게이션: Network-First → 오프라인이면 캐시된 index.html로 폴백
 *  - 교차 출처(카카오 지도 SDK, Lambda 날씨 API): 캐시하지 않고 항상 네트워크
 *    (날씨 데이터가 오래된 캐시로 보이는 것을 방지)
 *
 * 캐시 버전을 올리면(예: v1 -> v2) 이전 캐시가 자동 정리됩니다.
 */
const CACHE = 'weatherfit-cache-v1';
const PRECACHE_URLS = ['/', '/index.html'];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE)
            .then((cache) => cache.addAll(PRECACHE_URLS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const { request } = event;

    // GET 외 요청은 그대로 통과
    if (request.method !== 'GET') return;

    const url = new URL(request.url);

    // 교차 출처(API, 카카오 SDK 등)는 캐시 개입 없이 네트워크로
    if (url.origin !== self.location.origin) return;

    // SPA 내비게이션: 네트워크 우선, 실패 시 캐시된 index.html
    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request).catch(() => caches.match('/index.html'))
        );
        return;
    }

    // 그 외 같은 출처 정적 자산: Stale-While-Revalidate
    event.respondWith(
        caches.open(CACHE).then(async (cache) => {
            const cached = await cache.match(request);
            const network = fetch(request)
                .then((response) => {
                    if (response && response.ok) cache.put(request, response.clone());
                    return response;
                })
                .catch(() => cached);
            return cached || network;
        })
    );
});
