// BharatCompliance Service Worker v1
// Strategy: cache-first for static, network-first for pages/API

const STATIC_CACHE = 'bc-static-v1';
const PAGE_CACHE   = 'bc-pages-v1';
const OFFLINE_URL  = '/offline';

// ── Install ──────────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(PAGE_CACHE).then((cache) =>
      cache.addAll([OFFLINE_URL]).catch(() => {})
    ).then(() => self.skipWaiting())
  );
});

// ── Activate ─────────────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  const current = [STATIC_CACHE, PAGE_CACHE];
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => !current.includes(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// ── Fetch ─────────────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Only handle same-origin GET requests
  if (req.method !== 'GET' || url.origin !== location.origin) return;

  // Skip API proxy calls — always go to network
  if (url.pathname.startsWith('/api/') || isBackendCall(url.pathname)) return;

  // Next.js static assets (immutable, cache forever)
  if (url.pathname.startsWith('/_next/static/')) {
    event.respondWith(cacheFirst(req, STATIC_CACHE));
    return;
  }

  // Navigation requests — network-first, fallback to offline page
  if (req.mode === 'navigate') {
    event.respondWith(networkFirstWithOfflineFallback(req));
    return;
  }

  // Everything else — stale-while-revalidate
  event.respondWith(staleWhileRevalidate(req, PAGE_CACHE));
});

// ── Push Notifications (FCM via Web Push) ────────────────────────────
self.addEventListener('push', (event) => {
  if (!event.data) return;

  let data = {};
  try { data = event.data.json(); } catch { data = { title: 'BharatCompliance', body: event.data.text() }; }

  const options = {
    body:    data.body || 'You have a new notification.',
    icon:    '/icons/icon-192.svg',
    badge:   '/icons/icon-192.svg',
    tag:     data.tag || 'bc-notification',
    data:    data.url ? { url: data.url } : {},
    actions: data.actions || [],
    vibrate: [200, 100, 200],
  };

  event.waitUntil(self.registration.showNotification(data.title || 'BharatCompliance', options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || '/home';
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((windowClients) => {
      const existing = windowClients.find((c) => c.url.includes(targetUrl));
      if (existing) return existing.focus();
      return clients.openWindow(targetUrl);
    })
  );
});

// ── Cache strategies ──────────────────────────────────────────────────

async function cacheFirst(req, cacheName) {
  const cached = await caches.match(req);
  if (cached) return cached;
  const response = await fetch(req);
  if (response.ok) {
    const cache = await caches.open(cacheName);
    cache.put(req, response.clone());
  }
  return response;
}

async function networkFirstWithOfflineFallback(req) {
  try {
    const response = await fetch(req);
    if (response.ok) {
      const cache = await caches.open(PAGE_CACHE);
      cache.put(req, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(req);
    if (cached) return cached;
    const offline = await caches.match(OFFLINE_URL);
    return offline || new Response('Offline', { status: 503 });
  }
}

async function staleWhileRevalidate(req, cacheName) {
  const cache    = await caches.open(cacheName);
  const cached   = await cache.match(req);
  const fetchPromise = fetch(req).then((response) => {
    if (response.ok) cache.put(req, response.clone());
    return response;
  }).catch(() => null);

  return cached || fetchPromise || new Response('Not found', { status: 404 });
}

function isBackendCall(pathname) {
  const backendPrefixes = ['/auth/', '/clients/', '/transactions/', '/evidence/',
    '/dashboard/', '/compliance/', '/deadlines/', '/reminders/', '/whatsapp/',
    '/validation/', '/my/', '/invite/', '/orgs/'];
  return backendPrefixes.some((p) => pathname.startsWith(p));
}
