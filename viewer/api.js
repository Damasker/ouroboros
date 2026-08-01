/** Shared API helper — live server or static GitHub Pages export. */
(function (global) {
  const cfg = global.OUROBOROS || { mode: "live", dataBase: "/data" };

  function staticUrl(path) {
    const base = (cfg.dataBase || "/data").replace(/\/$/, "");
    if (path === "/health" || path === "health") return `${base}/health.json`;
    if (path === "/geometry" || path === "geometry") return `${base}/geometry.json`;
    if (path === "/client/protocol" || path === "/client/protocol/") {
      return `${base}/client/protocol.json`;
    }
    if (path === "/runs" || path === "runs") return `${base}/runs.json`;
    const mSnap = path.match(/^\/?runs\/([^/]+)\/snapshots\/?$/);
    if (mSnap) return `${base}/runs/${encodeURIComponent(mSnap[1])}/snapshots.json`;
    const mLatest = path.match(/^\/?runs\/([^/]+)\/snapshots\/latest\/?$/);
    if (mLatest) return `${base}/runs/${encodeURIComponent(mLatest[1])}/latest.json`;
    const mEnergy = path.match(/^\/?runs\/([^/]+)\/energy\/?$/);
    if (mEnergy) return `${base}/runs/${encodeURIComponent(mEnergy[1])}/energy.json`;
    const mStream = path.match(/^\/?runs\/([^/]+)\/client-stream\/?$/);
    if (mStream) return `${base}/runs/${encodeURIComponent(mStream[1])}/client-stream.json`;
    const mRun = path.match(/^\/?runs\/([^/]+)\/?$/);
    if (mRun) return `${base}/runs/${encodeURIComponent(mRun[1])}/meta.json`;
    return path;
  }

  /** Resolve a logical API path for fetch() or <a href>. */
  function hrefFor(path) {
    return cfg.mode === "static" ? staticUrl(path) : path;
  }

  async function apiJSON(path) {
    const url = hrefFor(path);
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${url} → ${r.status}`);
    return r.json();
  }

  /** Wire footer / protocol links so static Pages does not 404 on /health etc. */
  function bindStaticLinks(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-api-href]").forEach((el) => {
      const path = el.getAttribute("data-api-href");
      if (!path) return;
      el.setAttribute("href", hrefFor(path));
    });
  }

  global.OuroborosAPI = { apiJSON, staticUrl, hrefFor, bindStaticLinks, cfg };
})(window);
