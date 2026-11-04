/* Only here so that a phone that can't reach the PC gets a helpful page instead of a
 * browser error. Everything else goes straight to the network: nothing else is cached,
 * so lessons are never stale. */
"use strict";

const CACHE = "kaiwa-offline-1";
const OFFLINE_PAGE = "/static/offline.html";
const SERVER_DOWN = new Set([502, 503, 504]); // what `tailscale serve` answers with Kaiwa stopped

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.add(OFFLINE_PAGE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.mode !== "navigate") return;
  const offline = () => caches.match(OFFLINE_PAGE);
  event.respondWith(
    fetch(event.request)
      .then((response) => (SERVER_DOWN.has(response.status) ? offline() : response))
      .catch(offline)
  );
});
