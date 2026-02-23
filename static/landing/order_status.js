(function () {
  'use strict';
  var path = window.location.pathname.replace(/^\/order\//, '').replace(/\/$/, '');
  var orderId = path || null;
  var stateEl = document.getElementById('order-status-state');
  var resultsEl = document.getElementById('order-status-results');
  var gridEl = document.getElementById('museum-grid');
  var heroWrap = document.getElementById('museum-hero');
  var heroCaptionWrap = document.getElementById('museum-hero-caption');
  var downloadBtn = document.getElementById('order-status-download');
  var idEl = document.getElementById('order-status-id');
  var infoCardEl = document.getElementById('order-status-card-info');

  if (idEl) idEl.textContent = orderId || '—';

  function render(state, data) {
    if (!stateEl) return;
    if (state === 'loading') {
      stateEl.innerHTML = '<p class="order-status-loading">Se încarcă…</p>';
      resultsEl.style.display = 'none';
      infoCardEl.style.display = 'block';
      document.body.classList.remove('museum-mode');
      return;
    }
    if (state === 'processing') {
      stateEl.innerHTML = '<p class="order-status-processing">Opera ta se creează. De obicei durează 2–5 minute. Îți trimitem și un email când e gata.</p>';
      resultsEl.style.display = 'none';
      infoCardEl.style.display = 'block';
      document.body.classList.remove('museum-mode');
      return;
    }
    if (state === 'failed') {
      stateEl.innerHTML = '<div class="order-status-error">' + (data.error || 'Ceva nu a mers bine.') + '</div>';
      resultsEl.style.display = 'none';
      infoCardEl.style.display = 'block';
      document.body.classList.remove('museum-mode');
      return;
    }
    if (state === 'completed' && data.result_urls) {
      infoCardEl.style.display = 'none'; // Hide the white info card
      document.body.classList.add('museum-mode'); // Enable dark, immersive theme

      var urls = [];
      try {
        urls = typeof data.result_urls === 'string' ? JSON.parse(data.result_urls) : (data.result_urls || []);
      } catch (e) {
        urls = [];
      }
      var labels = data.result_labels || [];

      if (urls.length) {
        heroWrap.innerHTML = '';
        heroCaptionWrap.innerHTML = '';
        gridEl.innerHTML = '';

        // Render Hero Image
        if (urls[0]) {
          var heroImg = document.createElement('img');
          heroImg.src = urls[0];
          heroImg.alt = 'Opera Principală';
          heroImg.className = 'museum-hero-img';
          heroWrap.appendChild(heroImg);

          // Hero Caption (Title & Artist)
          var heroTitle = labels.length > 0 && labels[0][0] ? labels[0][0] : 'Capodoperă';
          var heroArtist = labels.length > 0 && labels[0][1] ? labels[0][1] : 'Artist Necunoscut';

          var titleEl = document.createElement('div');
          titleEl.className = 'museum-caption-title';
          titleEl.textContent = heroTitle;

          var artistEl = document.createElement('div');
          artistEl.className = 'museum-caption-artist';
          artistEl.textContent = heroArtist;

          heroCaptionWrap.appendChild(titleEl);
          heroCaptionWrap.appendChild(artistEl);
        }

        // Render Rest of Gallery Grid
        urls.forEach(function (url, i) {
          var tTitle = labels.length > i && labels[i][0] ? labels[i][0] : ('Opera ' + (i + 1));
          var tArtist = labels.length > i && labels[i][1] ? labels[i][1] : 'Artify';

          var a = document.createElement('a');
          a.href = url;
          a.target = '_blank';
          a.rel = 'noopener';
          a.className = 'museum-grid-item';

          var img = document.createElement('img');
          img.src = url;
          img.alt = tTitle;
          img.loading = 'lazy';

          var overlay = document.createElement('div');
          overlay.className = 'museum-grid-overlay';

          var itemTitle = document.createElement('div');
          itemTitle.className = 'museum-grid-title';
          itemTitle.textContent = tTitle;

          var itemArtist = document.createElement('div');
          itemArtist.className = 'museum-grid-artist';
          itemArtist.textContent = tArtist;

          overlay.appendChild(itemTitle);
          overlay.appendChild(itemArtist);

          a.appendChild(img);
          a.appendChild(overlay);
          gridEl.appendChild(a);
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
