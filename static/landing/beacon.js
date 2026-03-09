/**
 * Analytics beacon: sends path, section, time on page, session_id, referrer, UTM to /api/analytics/events.
 * Also pings /api/beacon for in-memory traffic. Only included on public pages (not dashboard or marketing).
 */
(function () {
    var STORAGE_KEY_VID = "artify_vid";
    var STORAGE_KEY_SID = "artify_sid";
    var THROTTLE_MS = 60000; // 1 request per 60s for visibility/interval
    var SESSION_IDLE_MS = 30 * 60 * 1000; // 30 min inactivity = new session
    var lastSent = 0;
    var pageEntryTime = typeof Date !== "undefined" ? Date.now() : 0;

    function getVid() {
        try {
            var vid = localStorage.getItem(STORAGE_KEY_VID);
            if (!vid) {
                vid = typeof crypto !== "undefined" && crypto.randomUUID
                    ? crypto.randomUUID()
                    : "x" + Math.random().toString(36).slice(2) + Date.now().toString(36);
                localStorage.setItem(STORAGE_KEY_VID, vid);
            }
            return vid;
        } catch (e) {
            return "x" + Math.random().toString(36).slice(2) + Date.now().toString(36);
        }
    }

    function getSessionId() {
        try {
            var sid = sessionStorage.getItem(STORAGE_KEY_SID);
            if (!sid) {
                sid = typeof crypto !== "undefined" && crypto.randomUUID
                    ? crypto.randomUUID()
                    : "s" + Math.random().toString(36).slice(2) + Date.now().toString(36);
                sessionStorage.setItem(STORAGE_KEY_SID, sid);
            }
            return sid;
        } catch (e) {
            return getVid();
        }
    }

    function getUtmParams() {
        var out = { utm_source: null, utm_medium: null, utm_campaign: null };
        if (typeof location === "undefined" || !location.search) return out;
        var q = location.search.slice(1).split("&");
        for (var i = 0; i < q.length; i++) {
            var parts = q[i].split("=");
            var key = decodeURIComponent(parts[0] || "").toLowerCase();
            var val = parts[1] != null ? decodeURIComponent(parts[1]) : "";
            if (key === "utm_source") out.utm_source = val.slice(0, 256);
            if (key === "utm_medium") out.utm_medium = val.slice(0, 256);
            if (key === "utm_campaign") out.utm_campaign = val.slice(0, 256);
        }
        return out;
    }

    function getDevice() {
        try {
            var ua = (typeof navigator !== "undefined" && navigator.userAgent) ? navigator.userAgent : "";
            if (/mobile|android|iphone|ipad|ipod|webos|blackberry|iemobile/i.test(ua)) return "mobile";
            return "desktop";
        } catch (e) {
            return null;
        }
    }

    function sendAnalyticsEvent(timeOnPageSec) {
        var path = (typeof location !== "undefined" && location.pathname) ? location.pathname : "/";
        var section = (typeof location !== "undefined" && location.hash) ? location.hash.slice(0, 256) : "";
        var vid = getVid();
        var sid = getSessionId();
        var utm = getUtmParams();
        var referrer = (typeof document !== "undefined" && document.referrer) ? document.referrer.slice(0, 1024) : "";
        var device = getDevice();
        var payload = {
            events: [{
                event_type: "page_view",
                path: path,
                section: section || null,
                time_on_page_sec: timeOnPageSec,
                session_id: sid,
                visitor_id: vid,
                referrer: referrer || null,
                utm_source: utm.utm_source || null,
                utm_medium: utm.utm_medium || null,
                utm_campaign: utm.utm_campaign || null,
                device: device
            }]
        };
        if (typeof fetch !== "undefined") {
            fetch("/api/analytics/events", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
                keepalive: true,
                credentials: "same-origin"
            }).catch(function () {});
        }
    }

    function sendBeaconPing() {
        var path = (typeof location !== "undefined" && location.pathname) ? location.pathname : "/";
        var section = (typeof location !== "undefined" && location.hash) ? location.hash : "";
        var vid = getVid();
        var sid = getSessionId();
        var q = "path=" + encodeURIComponent(path) + "&vid=" + encodeURIComponent(vid) + "&sid=" + encodeURIComponent(sid);
        if (section) q += "&section=" + encodeURIComponent(section);
        var url = "/api/beacon?" + q;
        if (typeof fetch !== "undefined") {
            fetch(url, { method: "GET", keepalive: true, credentials: "same-origin" }).catch(function () {});
        }
    }

    function sendPageView() {
        var now = Date.now();
        if (now - lastSent < 2000) return;
        lastSent = now;
        sendAnalyticsEvent(null);
        sendBeaconPing();
    }

    function onPageVisible() {
        if (Date.now() - lastSent >= THROTTLE_MS) sendPageView();
    }

    function onPageLeave() {
        var elapsed = (Date.now() - pageEntryTime) / 1000;
        if (elapsed > 0 && elapsed < 86400) sendAnalyticsEvent(elapsed);
    }

    if (typeof document === "undefined") return;
    pageEntryTime = Date.now();
    sendPageView();
    document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "visible") {
            onPageVisible();
        } else {
            onPageLeave();
        }
    });
    window.addEventListener("pagehide", onPageLeave);
    setInterval(function () {
        if (Date.now() - lastSent >= THROTTLE_MS) sendPageView();
    }, THROTTLE_MS);
})();
