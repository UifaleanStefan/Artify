(function () {
  'use strict';
  var path = window.location.pathname.replace(/^\/order\//, '').replace(/\/$/, '');
  var orderId = path || null;
  var stateEl = document.getElementById('order-status-state');
  var resultsEl = document.getElementById('order-status-results');
  var galleryEl = document.getElementById('order-status-gallery');
  var heroWrap = document.getElementById('order-status-hero-wrap');
  var downloadBtn = document.getElementById('order-status-download');
  var idEl = document.getElementById('order-status-id');

  if (idEl) idEl.textContent = orderId || '—';

  function render(state, data) {
    if (!stateEl) return;
    if (state === 'loading') {
      stateEl.innerHTML = '<p class="order-status-loading">Se încarcă…</p>';
      resultsEl.style.display = 'none';
      return;
    }
    if (state === 'processing') {
      stateEl.innerHTML = '<p class="order-status-processing">Opera ta se creează. De obicei durează 2–5 minute. Îți trimitem și un email când e gata.</p>';
      resultsEl.style.display = 'none';
      return;
    }
    if (state === 'failed') {
      stateEl.innerHTML = '<div class="order-status-error">' + (data.error || 'Ceva nu a mers bine.') + '</div>';
      resultsEl.style.display = 'none';
      return;
    }
    if (state === 'completed' && data.result_urls) {
      stateEl.innerHTML = '';
      var urls = [];
      try {
        urls = typeof data.result_urls === 'string' ? JSON.parse(data.result_urls) : (data.result_urls || []);
      } catch (e) {
        urls = [];
      }
      if (urls.length) {
        heroWrap.innerHTML = '';
        galleryEl.innerHTML = '';
        if (urls[0]) {
          var heroImg = document.createElement('img');
          heroImg.src = urls[0];
          heroImg.alt = 'Opera ta';
          heroWrap.appendChild(heroImg);
        }
        urls.forEach(function (url, i) {
          var a = document.createElement('a');
          a.href = url;
          a.target = '_blank';
          a.rel = 'noopener';
          a.title = 'Deschide imaginea ' + (i + 1);
          var img = document.createElement('img');
          img.src = url;
          img.alt = 'Opera ta ' + (i + 1);
          img.loading = 'lazy';
          a.appendChild(img);
          galleryEl.appendChild(a);
        });
        if (downloadBtn && orderId) {
          downloadBtn.href = '/api/orders/' + encodeURIComponent(orderId) + '/download-all';
        }
        resultsEl.style.display = 'block';
      }
      return;
    }
    stateEl.innerHTML = '<p class="order-status-loading">Status necunoscut.</p>';
  }

  function check() {
    if (!orderId) {
      render('failed', { error: 'Lipsă ID comandă în URL.' });
      return;
    }
    render('loading');
    fetch('/api/orders/' + encodeURIComponent(orderId) + '/status')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var status = (data.status || '').toLowerCase();
        if (status === 'completed') render('completed', data);
        else if (status === 'failed') render('failed', { error: data.error || 'Comanda a eșuat.' });
        else if (status === 'processing' || status === 'paid' || status === 'pending') render('processing');
        else render('failed', { error: data.detail || 'Comandă negăsită.' });
      })
      .catch(function () {
        render('failed', { error: 'Nu s-a putut încărca comanda. Verifică ID-ul și încearcă din nou.' });
      });
  }

  check();
})();
