/* sha-pay - Service Worker
   Caching strategy:
   - App shell (index.html, icons, manifest): cache-first
   - API calls: network ONLY, never cached (see the note below)
   - Mutating requests (POST/PATCH/DELETE): never intercepted
*/
const CACHE_NAME = "sha-pay-v7";

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

  // API responses are never cached, and are not intercepted at all: the request
  // goes straight to the network exactly as it would without a service worker.
  //
  // The Cache API keys on the request URL alone - the Authorization header is
  // not part of the key - so caching GET /api/v1/users/me served account A's
  // profile to account B on the same device (shared phones are the norm for
  // this app). Offline API data is not worth that; the calculator runs
  // client-side and does not need the network. Offline, the page shows its
  // normal error state instead of stale data from another user.
  if (url.pathname.startsWith("/api/")) {
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