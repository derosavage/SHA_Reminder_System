/* SHA Reminder - Service Worker
   Offline-first caching strategy:
   - App shell (index.html, icons, manifest): cache-first
   - API calls: network-first with cache fallback (read-only GET endpoints)
   - Never cache mutating requests (POST/PATCH/DELETE)
*/
const CACHE_NAME = "sha-reminder-v3";

// App shell resources to pre-cache on install.
const APP_SHELL = [
  "/",
  "/index.html",
  "/manifest.webmanifest",
  "/icons/logo.png",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/icon-maskable-512.png",
  "/icons/favicon-32.png",
];

// Install: pre-cache the app shell.
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

// Activate: clean up old caches and take control.
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Fetch: route by request type.
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin GET requests.
  if (request.method !== "GET" || url.origin !== self.location.origin) {
    return;
  }

  // API read-only endpoints: network-first, fall back to cache when offline.
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // App shell / static assets: cache-first, fall back to network then / offline page.
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request)
        .then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => {
          // Offline navigation fallback.
          if (request.mode === "navigate") {
            return caches.match("/");
          }
          return Response.error();
        });
    })
  );
});