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
  var globalStyleUrls = [];
  var globalLabels = [];
  var currentIndex = 0;

  if (idEl) idEl.textContent = orderId || '—';
  
  var shareWrapEl = document.getElementById('museum-share-wrap');
  var shareBtn = document.getElementById('museum-share-btn');
  
  if (shareBtn) {
    shareBtn.addEventListener('click', async function(e) {
      e.preventDefault();
      var imgUrl = globalUrls[currentIndex];
      if (!imgUrl) return;

      var tTitle = globalLabels.length > currentIndex && globalLabels[currentIndex][0] ? globalLabels[currentIndex][0] : 'Portretul meu Artify';
      var oldHtml = shareBtn.innerHTML;

      try {
        shareBtn.innerHTML = 'Se pregătește...';
        shareBtn.disabled = true;

        var response = await fetch(imgUrl);
        var blob = await response.blob();
        
        var ext = 'jpg';
        if (blob.type === 'image/png') ext = 'png';
        else if (blob.type === 'image/webp') ext = 'webp';
        
        var file = new File([blob], 'artify-portret.' + ext, { type: blob.type });

        if (navigator.canShare && navigator.canShare({ files: [file] })) {
          await navigator.share({
            files: [file],
            title: tTitle,
            text: 'Priviți noul meu portret artistic creat cu Artify! 🎨'
          });
        } else {
          // Fallback: trigger download
          var a = document.createElement('a');
          a.href = window.URL.createObjectURL(blob);
          a.download = 'artify-portret.' + ext;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('Error sharing', err);
        }
      } finally {
        shareBtn.innerHTML = oldHtml;
        shareBtn.disabled = false;
      }
    });
  }

  function triggerAnimation(el) {
    el.classList.remove('fade-enter');
    void el.offsetWidth; // force reflow
    el.classList.add('fade-enter');
  }

  function initSlider(wrap) {
    var divider = wrap.querySelector('.museum-compare-divider');
    if (!divider) return;

    var minPct = 5;
    var maxPct = 95;

    function setPct(pct) {
      pct = Math.max(minPct, Math.min(maxPct, pct));
      wrap.style.setProperty('--compare-pct', String(pct));
    }

    function onMove(e) {
      var rect = wrap.getBoundingClientRect();
      var x = e.clientX - rect.left;
      setPct((x / rect.width) * 100);
    }

    function stopDrag() {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', stopDrag);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    divider.addEventListener('mousedown', function (e) {
      e.preventDefault();
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', stopDrag);
      onMove(e);
    });

    wrap.addEventListener('touchstart', function (e) {
      if (e.target !== divider && !divider.contains(e.target)) return;
      e.preventDefault();
      var touch = e.touches[0];
      function touchMove(ev) {
        var t = ev.touches[0];
        var rect = wrap.getBoundingClientRect();
        var x = t.clientX - rect.left;
        setPct((x / rect.width) * 100);
      }
      function touchEnd() {
        wrap.removeEventListener('touchmove', touchMove);
        wrap.removeEventListener('touchend', touchEnd);
      }
      wrap.addEventListener('touchmove', touchMove, { passive: false });
      wrap.addEventListener('touchend', touchEnd);
      var rect = wrap.getBoundingClientRect();
      setPct(((touch.clientX - rect.left) / rect.width) * 100);
    }, { passive: false });
  }

  function showImage(index) {
    if (index < 0 || index >= globalUrls.length) return;
    currentIndex = index;
    
    var imgUrl = globalUrls[currentIndex];
    var styleImgUrl = null;
    
    if (globalStyleUrls && globalStyleUrls.length > 0) {
      styleImgUrl = globalStyleUrls.length > currentIndex ? globalStyleUrls[currentIndex] : globalStyleUrls[0];
    }
    
    if (styleImgUrl) {
      heroWrap.innerHTML = 
        '<div class="museum-compare-wrap" id="museum-compare-wrap">' +
          '<div class="museum-compare-before">' +
            '<img src="' + styleImgUrl + '" alt="Pictura originală" />' +
            '<span class="museum-compare-label museum-compare-label-right">Original</span>' +
          '</div>' +
          '<div class="museum-compare-after">' +
            '<img src="' + imgUrl + '" alt="Portretul tău" />' +
            '<span class="museum-compare-label museum-compare-label-left">Tu</span>' +
          '</div>' +
          '<div class="museum-compare-divider" id="museum-compare-divider">' +
            '<span class="museum-compare-handle">‖</span>' +
          '</div>' +
        '</div>';
      
      initSlider(document.getElementById('museum-compare-wrap'));
    } else {
      heroWrap.innerHTML = '<img src="' + imgUrl + '" class="museum-hero-img" alt="Operă" />';
    }
    
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
        // Safely scroll thumbnail into view without affecting body
        var scrollLeftTarget = thumb.offsetLeft - (filmstripEl.clientWidth / 2) + (thumb.clientWidth / 2);
        filmstripEl.scrollTo({ left: scrollLeftTarget, behavior: 'smooth' });
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
      try {
        globalStyleUrls = typeof data.style_image_urls === 'string' ? JSON.parse(data.style_image_urls) : (data.style_image_urls || []);
      } catch (e) {
        globalStyleUrls = [];
      }
      globalLabels = data.result_labels || [];

      if (globalUrls.length) {
        var packNameEl = document.getElementById('museum-pack-name');
        if (packNameEl) {
          if (data.style_name) {
            packNameEl.textContent = data.style_name;
            packNameEl.style.display = '';
          } else {
            packNameEl.style.display = 'none';
          }
        }

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

        if (shareWrapEl) {
          shareWrapEl.style.display = 'block';
        }

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
