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
  var doneTitle = document.getElementById('done-title');
  var doneSubtitle = document.getElementById('done-subtitle');
  var doneIcon = document.getElementById('done-icon');
  var doneMessage = document.getElementById('done-message');
  var doneMessageText = document.getElementById('done-message-text');
  var doneFirstResult = document.getElementById('done-first-result');
  var doneFirstResultLink = document.getElementById('done-first-result-link');
  var doneFirstResultImg = document.getElementById('done-first-result-img');

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

  if (orderId) {
    var pollTimer = null;
    var startedAt = Date.now();
    var maxPollMs = 10 * 60 * 1000; // stop polling after 10 minutes

    function showFirstImage(url) {
      if (doneTitle) doneTitle.textContent = 'Opera ta e gata!';
      if (doneSubtitle) doneSubtitle.textContent = 'Iată prima ta operă.';
      if (doneIcon) doneIcon.style.display = 'none';
      if (doneFirstResult && doneFirstResultLink && doneFirstResultImg) {
        doneFirstResultImg.src = url;
        doneFirstResultImg.alt = 'Opera ta';
        doneFirstResultLink.href = url;
        doneFirstResult.style.display = 'block';
      }
      if (doneMessageText) doneMessageText.textContent = 'Restul operelor ți le trimitem pe email.';
    }

    function stopPolling() {
      if (pollTimer) {
        clearTimeout(pollTimer);
        pollTimer = null;
      }
    }

    function scheduleNextPoll() {
      if (Date.now() - startedAt > maxPollMs) return;
      pollTimer = setTimeout(fetchStatus, 8000);
    }

    function fetchStatus() {
      fetch('/api/orders/' + encodeURIComponent(orderId) + '/status')
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var status = (data.status || '').toLowerCase();
          var resultUrls = data.result_urls;
          var urls = [];
          if (resultUrls) {
            try { urls = typeof resultUrls === 'string' ? JSON.parse(resultUrls) : (resultUrls || []); } catch (e) {}
          }

          if (urls.length > 0) {
            showFirstImage(urls[0]);
            stopPolling();
            return;
          }

          if (status === 'failed' && data.error) {
            if (doneMessageText) doneMessageText.textContent = 'Something went wrong: ' + data.error;
            stopPolling();
            return;
          }

          scheduleNextPoll();
        })
        .catch(function () {
          scheduleNextPoll();
        });
    }

    fetchStatus();
  }
})();
