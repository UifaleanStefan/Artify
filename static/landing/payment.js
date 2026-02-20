(function () {
  'use strict';
  var data = window.STYLES_DATA || [];
  var params = new URLSearchParams(window.location.search);
  var styleId = params.get('style');
  var imageUrl = params.get('image_url');
  var email = params.get('email') || '';
  var style = null;

  if (styleId) { var id = parseInt(styleId, 10); style = data.find(function (s) { return s.id === id; }); }

  var thumb = document.getElementById('payment-style-thumb');
  var tag = document.getElementById('payment-style-tag');
  var name = document.getElementById('payment-style-name');
  var deliveryEl = document.getElementById('payment-delivery');
  var backLink = document.getElementById('payment-back');
  var payBtn = document.getElementById('payment-pay-btn');

  if (style) {
    if (thumb) thumb.className = 'payment-style-thumb ' + (style.thumbnailClass || '');
    if (tag) { tag.textContent = style.category; var catKey = style.category ? style.category.toLowerCase().replace(/[\s-]+/g, '') : ''; tag.className = 'payment-style-tag tag-' + catKey; }
    if (name) name.textContent = style.title;
  }
  if (deliveryEl) deliveryEl.textContent = email || '—';
  if (backLink) {
    var q = '?style=' + encodeURIComponent(styleId || '') + '&image_url=' + encodeURIComponent(imageUrl || '') + '&email=' + encodeURIComponent(email);
    backLink.href = '/billing' + q;
  }

  if (payBtn) {
    payBtn.addEventListener('click', function () {
      if (!styleId || !imageUrl) { alert('Order data is missing. Please start from the beginning.'); window.location.href = '/styles'; return; }
      if (!style || !style.styleImageUrl) { alert('Style data is missing. Please contact support.'); return; }
      if (!email) { alert('Email is required. Please go back to Details.'); return; }
      var billingInfoStr = sessionStorage.getItem('billingInfo');
      if (!billingInfoStr) { alert('Billing information is missing. Please go back to Billing.'); return; }
      var billingInfo = JSON.parse(billingInfoStr);
      payBtn.disabled = true; payBtn.textContent = 'Processing…';

      fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email,
          style_id: parseInt(styleId, 10),
          image_url: imageUrl,
          billing_name: billingInfo.fullName,
          billing_address: billingInfo.address1 + (billingInfo.address2 ? ', ' + billingInfo.address2 : ''),
          billing_city: billingInfo.city,
          billing_state: billingInfo.state,
          billing_zip: billingInfo.zip,
          billing_country: billingInfo.country
        })
      })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok) throw new Error((res.data && res.data.detail) || 'Failed to create order.');
        var orderId = res.data && res.data.order_id;
        if (!orderId) throw new Error('Order created but no order_id returned.');
        return fetch('/api/orders/' + encodeURIComponent(orderId) + '/pay', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ payment_provider: 'stripe', transaction_id: 'TXN-' + Date.now() })
        }).then(function (r) { return r.json().catch(function () { return {}; }).then(function (d) { return { ok: r.ok, data: d, orderId: orderId }; }); });
      })
      .then(function (res) {
        if (!res.ok) throw new Error((res.data && res.data.detail) || 'Payment failed.');
        var q = '?order_id=' + encodeURIComponent(res.orderId) + '&style=' + encodeURIComponent(styleId) + '&email=' + encodeURIComponent(email);
        window.location.href = '/create/done' + q;
      })
      .catch(function (err) {
        payBtn.disabled = false; payBtn.textContent = 'Pay $12.00';
        alert(err.message || 'Something went wrong.');
      });
    });
  }
})();
