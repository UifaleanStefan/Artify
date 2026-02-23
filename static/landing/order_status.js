(function () {
  'use strict';
  var path = window.location.pathname.replace(/^\/order\//, '').replace(/\/$/, '');
  var orderId = path || null;
  var stateEl = document.getElementById('order-status-state');
  var resultsEl = document.getElementById('order-status-results');
  var filmstripEl = document.getElementById('museum-filmstrip');
  var heroWrap = document.getElementById('museum-hero');
  var heroCaptionWrap = document.getElementById('museum-hero-caption');
  var downloadBtn = document.getElementById('order-status-download');
  var idEl = document.getElementById('order-status-id');
  var infoCardEl = document.getElementById('order-status-card-info');
  
  var prevBtn = document.getElementById('exhibition-prev');
  var nextBtn = document.getElementById('exhibition-next');
  
  var globalUrls = [];
  var globalLabels = [];
  var currentIndex = 0;

  if (idEl) idEl.textContent = orderId || '—';
  
  function triggerAnimation(el) {
    el.classList.remove('fade-enter');
    void el.offsetWidth; // force reflow
    el.classList.add('fade-enter');
  }

  function showImage(index) {
    if (index < 0 || index >= globalUrls.length) return;
    currentIndex = index;
    
    // Update hero image
    var imgUrl = globalUrls[currentIndex];
    heroWrap.innerHTML = '<img src="' + imgUrl + '" class="museum-hero-img" alt="Operă" />';
    
    // Update caption
    var tTitle = globalLabels.length > currentIndex && globalLabels[currentIndex][0] ? globalLabels[currentIndex][0] : ('Opera ' + (currentIndex + 1));
    var tArtist = globalLabels.length > currentIndex && globalLabels[currentIndex][1] ? globalLabels[currentIndex][1] : 'Artify';
    
    heroCaptionWrap.innerHTML = 
      '<div class="museum-caption-title">' + tTitle + '</div>' +
      '<div class="museum-caption-artist">' + tArtist + '</div>';
      
    triggerAnimation(heroWrap);
    triggerAnimation(heroCaptionWrap);
    
    // Update active state on filmstrip
    var thumbs = filmstripEl.querySelectorAll('.filmstrip-item');
    thumbs.forEach(function(thumb, i) {
      if (i === currentIndex) {
        thumb.classList.add('active');
        // Scroll thumbnail into view smoothly if needed
        thumb.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      } else {
        thumb.classList.remove('active');
      }
    });
    
    // Update arrow states
    if (prevBtn) prevBtn.disabled = (currentIndex === 0);
    if (nextBtn) nextBtn.disabled = (currentIndex === globalUrls.length - 1);
  }

  if (prevBtn) {
    prevBtn.addEventListener('click', function(e) {
      e.preventDefault();
      if (currentIndex > 0) showImage(currentIndex - 1);
    });
  }
  
  if (nextBtn) {
    nextBtn.addEventListener('click', function(e) {
      e.preventDefault();
      if (currentIndex < globalUrls.length - 1) showImage(currentIndex + 1);
    });
  }

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
      infoCardEl.style.display = 'none';
      document.body.classList.add('museum-mode');

      try {
        globalUrls = typeof data.result_urls === 'string' ? JSON.parse(data.result_urls) : (data.result_urls || []);
      } catch (e) {
        globalUrls = [];
      }
      globalLabels = data.result_labels || [];

      if (globalUrls.length) {
        filmstripEl.innerHTML = '';
        
        globalUrls.forEach(function (url, i) {
          var btn = document.createElement('button');
          btn.className = 'filmstrip-item';
          btn.onclick = function() { showImage(i); };
          
          var img = document.createElement('img');
          img.src = url;
          img.alt = 'Thumbnail ' + (i + 1);
          img.loading = 'lazy';
          
          btn.appendChild(img);
          filmstripEl.appendChild(btn);
        });

        // Initialize first image
        currentIndex = 0;
        showImage(0);

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
