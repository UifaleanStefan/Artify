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
  var doneMessageText = document.getElementById('done-message-text');

  if (orderIdEl) orderIdEl.textContent = orderId || '—';
  if (styleNameEl) styleNameEl.textContent = style ? (style.title + ' – ' + style.artist) : '—';
  if (emailEl) emailEl.textContent = email || '—';
  var emailHighlight = document.getElementById('done-email-highlight');
  if (emailHighlight) emailHighlight.textContent = email || '—';

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
    var paymentConfirmedAt = null;
    var paymentConfirmedMaxWait = 3 * 60 * 1000; // if paid/processing for 3+ minutes, stop polling

    function onGalleryReady() {
      if (doneTitle) doneTitle.textContent = 'Galeria ta e gata!';
      if (doneSubtitle) doneSubtitle.textContent = 'Verifică emailul – acolo ai linkul către galerie.';
      if (doneMessageText) doneMessageText.textContent = 'Am trimis un email la ' + (email || 'tine') + ' cu linkul către galerie. Verifică inbox-ul și dosarul Spam.';
    }

    function onPaymentConfirmed() {
      // Payment is confirmed, show success message and stop polling after reasonable time
      if (doneTitle) doneTitle.textContent = 'Plată confirmată! 🎨';
      if (doneSubtitle) doneSubtitle.textContent = 'Portretul tău se creează acum. Vei primi rezultatele pe email în câteva minute.';
      if (doneMessageText) doneMessageText.textContent = 'Îți trimitem toate portretele pe email la ' + (email || 'adresa ta') + '. Verifică inbox-ul și dosarul Spam. Nu este necesar să aștepți pe această pagină.';
    }

    function stopPolling() {
      if (pollTimer) {
        clearTimeout(pollTimer);
        pollTimer = null;
      }
    }

    function scheduleNextPoll() {
      if (Date.now() - startedAt > maxPollMs) {
        // Max polling time reached
        if (paymentConfirmedAt && !doneTitle.textContent.includes('gata')) {
          onPaymentConfirmed();
        }
        return;
      }
      // If payment was confirmed but we've been waiting too long, stop polling
      if (paymentConfirmedAt && (Date.now() - paymentConfirmedAt) > paymentConfirmedMaxWait) {
        onPaymentConfirmed();
        stopPolling();
        return;
      }
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
            onGalleryReady();
            stopPolling();
            return;
          }

          if (status === 'failed' && data.error) {
            if (doneMessageText) doneMessageText.textContent = 'Ceva nu a mers bine: ' + (data.error || 'Eroare necunoscută') + '. Contactează-ne la artify.system@gmail.com cu ID-ul comenzii: ' + orderId;
            if (doneTitle) doneTitle.textContent = 'Eroare la procesare';
            stopPolling();
            return;
          }

          // Payment is confirmed (paid or processing)
          if ((status === 'paid' || status === 'processing') && !paymentConfirmedAt) {
            paymentConfirmedAt = Date.now();
            onPaymentConfirmed();
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
