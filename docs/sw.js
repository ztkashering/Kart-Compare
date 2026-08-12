
const CACHE_NAME = "kartcompare-shell-2026-08-12-153526";
const SHELL_FILES = ["index.html", "manifest.json", "icon-192.png", "icon-512.png"];

self.addEventListener("install", (event) => {
  // NOT cache.addAll(SHELL_FILES) on purpose (found 2026-08-11): addAll()
  // fetches with the browser's default HTTP cache mode, which can itself
  // return an old disk-cached or CDN-edge-cached copy of index.html even
  // though CACHE_NAME changed and this install step is genuinely running
  // fresh -- the new Cache Storage bucket would just get seeded with
  // stale content again. Fetching with {cache: "reload"} forces each
  // shell file to go all the way to the network, bypassing HTTP cache,
  // so what actually lands in the new bucket is really current.
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      Promise.all(
        SHELL_FILES.map((url) =>
          fetch(url, { cache: "reload" }).then((res) => {
            cache.put(url, res.clone());
            // Also found 2026-08-11: a plain navigation to the site root
            // ("/Kart-Compare/") is a DIFFERENT request URL than
            // "index.html", so caches.match() in the fetch handler below
            // was never actually finding this cached entry for real
            // visits -- it silently fell through to a live (cacheable-
            // by-the-browser) network fetch every time instead of using
            // this cache at all. Storing the same response under the
            // scope URL too fixes that.
            if (url === "index.html") cache.put(self.registration.scope, res.clone());
          })
        )
      )
    ).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  // Never cache the live deals data -- always go to the network for that.
  if (event.request.url.includes("deals.json")) return;
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
