(function () {
  'use strict';
  var data = window.STYLES_DATA || [];
  var params = new URLSearchParams(window.location.search);
  var orderId = params.get('order_id');
  var styleId = params.get('style');
  var email = params.get('email') || '';
  var style = null;

  if (styleId) { var id = parseInt(styleId, 10); style = data.find(function (s) { return s.id === id; }); }

  var orderIdEl = document.getElementById('done-order-id');
  var styleNameEl = document.getElementById('done-style-name');
  var emailEl = document.getElementById('done-email');
  var copyBtn = document.getElementById('done-copy-btn');

  if (orderIdEl) orderIdEl.textContent = orderId || '—';
  if (styleNameEl) styleNameEl.textContent = style ? (style.title + ' – ' + style.artist) : '—';
  if (emailEl) emailEl.textContent = email || '—';

  if (copyBtn && orderId) {
    copyBtn.addEventListener('click', function () {
      navigator.clipboard.writeText(orderId).then(function () { copyBtn.textContent = '✓'; setTimeout(function () { copyBtn.textContent = '📋'; }, 2000); });
    });
  }
  var viewStatusWrap = document.getElementById('done-view-status-wrap');
  var viewStatusLink = document.getElementById('done-view-status-link');
  if (orderId && viewStatusWrap && viewStatusLink) {
    viewStatusLink.href = '/order/' + encodeURIComponent(orderId);
    viewStatusWrap.style.display = 'block';
  }
})();
