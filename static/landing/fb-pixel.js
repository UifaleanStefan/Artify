/**
 * Facebook Pixel: loads only when FACEBOOK_PIXEL_ID is set via /api/config/public.
 * Fires PageView on load; optional ViewContent / InitiateCheckout by path.
 * Exposes __fbqPurchase(value, currency) for payment success page (one-shot per load).
 */
(function () {
    var purchaseFired = false;

    function injectFbqAndInit(pixelId) {
        if (typeof window === "undefined" || window.fbq) return;
        (function (f, b, e, v, n, t, s) {
            if (f.fbq) return;
            n = f.fbq = function () {
                n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
            };
            if (!f._fbq) f._fbq = n;
            n.push = n;
            n.loaded = !0;
            n.version = "2.0";
            n.queue = [];
            t = b.createElement(e);
            t.async = !0;
            t.src = v;
            s = b.getElementsByTagName(e)[0];
            s.parentNode.insertBefore(t, s);
        })(window, document, "script", "https://connect.facebook.net/en_US/fbevents.js");
        window.fbq("init", pixelId);
        window.fbq("track", "PageView");

        var path = (typeof location !== "undefined" && location.pathname) ? location.pathname.replace(/\/$/, "") || "/" : "/";
        var viewContentPayload = {
            content_type: "product",
            currency: "RON"
        };
        if (path === "/" || path === "") {
            viewContentPayload.content_name = "Home";
            viewContentPayload.content_ids = ["home"];
            viewContentPayload.content_category = "landing";
            viewContentPayload.value = 0;
            window.fbq("track", "ViewContent", viewContentPayload);
        } else if (path.indexOf("/styles") === 0) {
            viewContentPayload.content_name = "Styles";
            viewContentPayload.content_ids = ["styles"];
            viewContentPayload.content_category = "product";
            viewContentPayload.value = 9.99;
            window.fbq("track", "ViewContent", viewContentPayload);
        } else if (path === "/details") {
            viewContentPayload.content_name = "Details";
            viewContentPayload.content_ids = ["details"];
            viewContentPayload.content_category = "product";
            viewContentPayload.value = 9.99;
            window.fbq("track", "ViewContent", viewContentPayload);
        } else if (path.indexOf("/upload") === 0) {
            viewContentPayload.content_name = "Upload";
            viewContentPayload.content_ids = ["upload"];
            viewContentPayload.content_category = "product";
            viewContentPayload.value = 9.99;
            window.fbq("track", "ViewContent", viewContentPayload);
        }
        if (path === "/billing" || path === "/payment") {
            window.fbq("track", "InitiateCheckout");
        }
    }

    window.__fbqPurchase = function (value, currency) {
        if (purchaseFired) return;
        purchaseFired = true;
        if (typeof window.fbq !== "function") return;
        window.fbq("track", "Purchase", {
            value: value,
            currency: (currency || "RON").toUpperCase()
        });
    };

    var id = (typeof window !== "undefined" && window.__FB_PIXEL_ID) ? window.__FB_PIXEL_ID : "";
    if (id && typeof id === "string" && id.trim()) {
        injectFbqAndInit(id.trim());
        return;
    }
    if (typeof fetch === "undefined") return;
    fetch("/api/config/public", { credentials: "same-origin" })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var fid = data && data.facebook_pixel_id;
            if (fid && typeof fid === "string" && fid.trim()) {
                injectFbqAndInit(fid.trim());
            }
        })
        .catch(function () {});
})();
