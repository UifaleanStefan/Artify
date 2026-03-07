/**
 * Lightweight traffic beacon: sends path + optional section to /api/beacon.
 * Only included on public pages (not dashboard or marketing).
 */
(function () {
    var STORAGE_KEY = "artify_vid";
    var THROTTLE_MS = 60000; // 1 request per 60s for visibility/interval
    var lastSent = 0;

    function getVid() {
        try {
            var vid = localStorage.getItem(STORAGE_KEY);
            if (!vid) {
                vid = typeof crypto !== "undefined" && crypto.randomUUID
                    ? crypto.randomUUID()
                    : "x" + Math.random().toString(36).slice(2) + Date.now().toString(36);
                localStorage.setItem(STORAGE_KEY, vid);
            }
            return vid;
        } catch (e) {
            return "x" + Math.random().toString(36).slice(2) + Date.now().toString(36);
        }
    }

    function sendBeacon() {
        var now = Date.now();
        if (now - lastSent < 2000) return; // at least 2s between any sends
        lastSent = now;
        var path = (typeof location !== "undefined" && location.pathname) ? location.pathname : "/";
        var section = (typeof location !== "undefined" && location.hash) ? location.hash : "";
        var vid = getVid();
        var q = "path=" + encodeURIComponent(path) + "&vid=" + encodeURIComponent(vid);
        if (section) q += "&section=" + encodeURIComponent(section);
        var url = "/api/beacon?" + q;
        if (typeof fetch !== "undefined") {
            fetch(url, { method: "GET", keepalive: true, credentials: "same-origin" }).catch(function () {});
        }
    }

    function throttledSend() {
        if (Date.now() - lastSent >= THROTTLE_MS) sendBeacon();
    }

    if (typeof document === "undefined") return;
    sendBeacon();
    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "visible") throttledSend();
    });
    setInterval(throttledSend, THROTTLE_MS);
})();
