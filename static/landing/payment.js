(function () {
  'use strict';
  var data = window.STYLES_DATA || [];
  var params = new URLSearchParams(window.location.search);
  var styleId = params.get('style');
  var imageUrl = params.get('image_url');
  var portraitMode = params.get('portrait_mode') || 'realistic';
  var email = params.get('email') || '';
  var pack = params.get('pack') || '5';
  if (pack !== '5' && pack !== '15') pack = '5';
  var priceStr = pack === '15' ? '79,99 Lei' : '9,99 Lei';
  var style = null;

  if (styleId) { var id = parseInt(styleId, 10); style = data.find(function (s) { return s.id === id; }); }

  var thumb = document.getElementById('payment-style-thumb');
  var tag = document.getElementById('payment-style-tag');
  var name = document.getElementById('payment-style-name');
  var deliveryEl = document.getElementById('payment-delivery');
  var backLink = document.getElementById('payment-back');
  var payBtn = document.getElementById('payment-pay-btn');
  var thumbPrev = document.getElementById('payment-thumb-prev');
  var thumbNext = document.getElementById('payment-thumb-next');

  function fillPackThumb(el, s, prevBtn, nextBtn) {
    var isMasters = Number(s.id) === 13;
    var mastersUrls = ['/static/landing/styles/masters/masters-01.jpg', '/static/landing/styles/masters/masters-02.jpg', '/static/landing/styles/masters/masters-03.jpg', '/static/landing/styles/masters/masters-04.jpg', '/static/landing/styles/masters/masters-05.jpg'];
    var previewUrls = (s.previewImageUrls && s.previewImageUrls.length) ? s.previewImageUrls : (isMasters ? mastersUrls : null);
    if (previewUrls && previewUrls.length) {
      el.className = 'payment-style-thumb style-thumb-h-scroll';
      el.innerHTML = '';
      previewUrls.forEach(function (url) {
        var img = document.createElement('img');
        img.src = url;
        img.alt = s.title || 'Style';
        el.appendChild(img);
      });
      if (prevBtn) { prevBtn.style.display = 'flex'; prevBtn.classList.add('show'); prevBtn.onclick = function () { el.scrollBy({ left: -el.clientWidth, behavior: 'smooth' }); }; }
      if (nextBtn) { nextBtn.style.display = 'flex'; nextBtn.classList.add('show'); nextBtn.onclick = function () { el.scrollBy({ left: el.clientWidth, behavior: 'smooth' }); }; }
    } else if (s.styleImageUrl) {
      el.className = 'payment-style-thumb style-thumb-single';
      el.innerHTML = '<img src="' + s.styleImageUrl + '" alt="' + (s.title || 'Style') + '" />';
      if (prevBtn) prevBtn.style.display = 'none';
      if (nextBtn) nextBtn.style.display = 'none';
    } else {
      el.className = 'payment-style-thumb ' + (s.thumbnailClass || '');
      el.innerHTML = '';
      if (prevBtn) prevBtn.style.display = 'none';
      if (nextBtn) nextBtn.style.display = 'none';
    }
  }

  if (style) {
    if (thumb) fillPackThumb(thumb, style, thumbPrev, thumbNext);
    if (tag) { tag.textContent = style.category; var catKey = style.category ? style.category.toLowerCase().replace(/[\s-]+/g, '') : ''; tag.className = 'payment-style-tag tag-' + catKey; }
    if (name) name.textContent = style.title;
  }
  if (deliveryEl) deliveryEl.textContent = email || '—';
  var paymentPriceEl = document.getElementById('payment-price');
  var paymentTotalEl = document.getElementById('payment-total');
  if (paymentPriceEl) paymentPriceEl.textContent = priceStr;
  if (paymentTotalEl) paymentTotalEl.textContent = priceStr;
  if (payBtn) payBtn.textContent = 'Plătește ' + priceStr;
  if (backLink) {
    var q = '?style=' + encodeURIComponent(styleId || '') + '&image_url=' + encodeURIComponent(imageUrl || '') + '&portrait_mode=' + encodeURIComponent(portraitMode) + '&email=' + encodeURIComponent(email) + '&pack=' + encodeURIComponent(pack);
    backLink.href = '/billing' + q;
  }

  if (payBtn) {
    payBtn.addEventListener('click', function () {
      if (!styleId || !imageUrl) { alert('Lipsesc datele comenzii. Te rugăm să începi de la început.'); window.location.href = '/styles'; return; }
      if (!style || !style.styleImageUrl) { alert('Lipsesc datele stilului. Contactează suportul.'); return; }
      if (!email) { alert('Emailul este obligatoriu. Revino la Detalii.'); return; }
      var billingInfoStr = sessionStorage.getItem('billingInfo');
      if (!billingInfoStr) { alert('Lipsesc datele de facturare. Revino la Facturare.'); return; }
      var billingInfo = JSON.parse(billingInfoStr);
      payBtn.disabled = true; payBtn.textContent = 'Se procesează…';

      fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email,
          style_id: parseInt(styleId, 10),
          image_url: imageUrl,
          portrait_mode: portraitMode,
          pack_tier: parseInt(pack, 10) || 5,
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
        if (!res.ok) throw new Error((res.data && res.data.detail) || 'Crearea comenzii a eșuat.');
        var orderId = res.data && res.data.order_id;
        if (!orderId) throw new Error('Comanda a fost creată dar nu s-a returnat order_id.');
        return fetch('/api/orders/' + encodeURIComponent(orderId) + '/pay', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ payment_provider: 'stripe', transaction_id: 'TXN-' + Date.now() })
        }).then(function (r) { return r.json().catch(function () { return {}; }).then(function (d) { return { ok: r.ok, data: d, orderId: orderId }; }); });
      })
      .then(function (res) {
        if (!res.ok) throw new Error((res.data && res.data.detail) || 'Plata a eșuat.');
        var q = '?order_id=' + encodeURIComponent(res.orderId) + '&style=' + encodeURIComponent(styleId) + '&email=' + encodeURIComponent(email);
        window.location.href = '/create/done' + q;
      })
      .catch(function (err) {
        payBtn.disabled = false; payBtn.textContent = 'Plătește ' + priceStr;
        alert(err.message || 'Ceva nu a mers bine.');
      });
    });
  }
})();
