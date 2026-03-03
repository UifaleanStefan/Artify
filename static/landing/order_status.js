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

        var siteUrl = window.location.origin;
        var shareData = {
          files: [file],
          title: tTitle,
          text: 'Priviți noul meu portret artistic creat cu Artify! 🎨 ' + siteUrl
        };
        if (navigator.canShare && navigator.canShare({ files: [file] })) {
          await navigator.share(shareData);
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
    var isDragging = false;

    function setPct(pct) {
      pct = Math.max(minPct, Math.min(maxPct, pct));
      wrap.style.setProperty('--compare-pct', String(pct));
    }

    function moveToPosition(clientX) {
      var rect = wrap.getBoundingClientRect();
      var x = clientX - rect.left;
      setPct((x / rect.width) * 100);
    }

    function onMove(e) {
      var rect = wrap.getBoundingClientRect();
      var x = e.clientX - rect.left;
      setPct((x / rect.width) * 100);
    }

    function stopDrag() {
      isDragging = false;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', stopDrag);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    /* Click anywhere on image to move slider there */
    wrap.addEventListener('click', function (e) {
      if (isDragging) return;
      moveToPosition(e.clientX);
    });

    divider.addEventListener('mousedown', function (e) {
      e.preventDefault();
      isDragging = true;
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', stopDrag);
      onMove(e);
    });

    /* Touch: tap anywhere to move, or drag handle */
    wrap.addEventListener('touchstart', function (e) {
      var touch = e.touches[0];
      var touchedDivider = e.target === divider || divider.contains(e.target);
      var startX = touch.clientX;
      var startTime = Date.now();
      var moved = false;

      function touchMove(ev) {
        if (!touchedDivider) return;
        moved = true;
        ev.preventDefault();
        var t = ev.touches[0];
        var rect = wrap.getBoundingClientRect();
        setPct(((t.clientX - rect.left) / rect.width) * 100);
      }
      function touchEnd(ev) {
        wrap.removeEventListener('touchmove', touchMove);
        wrap.removeEventListener('touchend', touchEnd);
        /* If short tap with little movement, move slider to tap position */
        if (!moved && ev.changedTouches && ev.changedTouches[0] && Date.now() - startTime < 400) {
          var endX = ev.changedTouches[0].clientX;
          if (Math.abs(endX - startX) < 15) {
            moveToPosition(ev.changedTouches[0].clientX);
          }
        }
      }

      if (touchedDivider) {
        e.preventDefault();
        var rect = wrap.getBoundingClientRect();
        setPct(((touch.clientX - rect.left) / rect.width) * 100);
      }
      wrap.addEventListener('touchmove', touchMove, { passive: false });
      wrap.addEventListener('touchend', touchEnd, { passive: true });
    }, { passive: true });
  }

  function showImage(index) {
    if (index < 0 || index >= globalUrls.length) return;
    currentIndex = index;
    
    var imgUrl = globalUrls[currentIndex];
    var styleImgUrl = null;
    
    if (globalStyleUrls && globalStyleUrls.length > currentIndex) {
      styleImgUrl = globalStyleUrls[currentIndex];
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
    console.log('Render called with state:', state, 'data:', data);
    if (!stateEl) {
      console.error('stateEl not found!');
      return;
    }
    if (state === 'loading') {
      stateEl.innerHTML = '<p class="order-status-loading">Se încarcă…</p>';
      if (resultsEl) resultsEl.style.display = 'none';
      if (infoCardEl) infoCardEl.style.display = 'block';
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
        console.error('Error parsing result_urls:', e, data.result_urls);
        globalUrls = [];
      }
      try {
        globalStyleUrls = typeof data.style_image_urls === 'string' ? JSON.parse(data.style_image_urls) : (data.style_image_urls || []);
      } catch (e) {
        console.error('Error parsing style_image_urls:', e, data.style_image_urls);
        globalStyleUrls = [];
      }
      globalLabels = data.result_labels || [];

      if (!globalUrls || globalUrls.length === 0) {
        console.error('No result URLs found for completed order:', data);
        render('failed', { error: 'Comanda este completă dar nu are imagini rezultate. Contactează-ne la artify.system@gmail.com cu ID-ul: ' + orderId });
        return;
      }

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

        // Nudge filmstrip to hint it's scrollable
        (function nudgeFilmstrip() {
          var el = filmstripEl;
          if (!el) return;
          var distance = 120;
          var duration = 600;
          setTimeout(function() {
            var start = null;
            var startLeft = 0;
            function stepFwd(ts) {
              if (!start) start = ts;
              var p = Math.min((ts - start) / duration, 1);
              var e = p < 0.5 ? 2*p*p : -1 + (4 - 2*p)*p;
              el.scrollLeft = startLeft + distance * e;
              if (p < 1) { requestAnimationFrame(stepFwd); }
              else {
                var start2 = null; var fromLeft = el.scrollLeft;
                function stepBack(ts2) {
                  if (!start2) start2 = ts2;
                  var p2 = Math.min((ts2 - start2) / duration, 1);
                  var e2 = p2 < 0.5 ? 2*p2*p2 : -1 + (4 - 2*p2)*p2;
                  el.scrollLeft = fromLeft - distance * e2;
                  if (p2 < 1) requestAnimationFrame(stepBack);
                }
                requestAnimationFrame(stepBack);
              }
            }
            requestAnimationFrame(stepFwd);
          }, 800);
        })();

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
    console.log('Checking order status for:', orderId);
    render('loading');
    var apiUrl = '/api/orders/' + encodeURIComponent(orderId) + '/status';
    console.log('Fetching:', apiUrl);
    fetch(apiUrl)
      .then(function (r) {
        if (!r.ok) {
          if (r.status === 404) {
            render('failed', { error: 'Comandă negăsită. Verifică ID-ul comenzii: ' + orderId });
            return null; // Return null to prevent further processing
          } else {
            return r.json().then(function(data) {
              render('failed', { error: data.detail || 'Eroare la încărcarea comenzii.' });
              return null; // Return null to prevent further processing
            });
          }
        }
        return r.json();
      })
      .then(function (data) {
        if (!data) return; // Already handled error case
        console.log('Order status response:', data);
        var status = (data.status || '').toLowerCase();
        if (status === 'completed') {
          if (!data.result_urls) {
            console.warn('Order completed but no result_urls:', data);
            render('failed', { error: 'Comanda este completă dar nu are imagini rezultate. Contactează-ne la artify.system@gmail.com' });
            return;
          }
          render('completed', data);
        } else if (status === 'failed') {
          render('failed', { error: data.error || 'Comanda a eșuat.' });
        } else if (status === 'processing' || status === 'paid' || status === 'pending') {
          render('processing');
        } else {
          console.warn('Unknown order status:', status, data);
          render('failed', { error: data.detail || 'Status necunoscut pentru comandă: ' + status });
        }
      })
      .catch(function (err) {
        console.error('Error fetching order status:', err);
        render('failed', { error: 'Nu s-a putut încărca comanda. Verifică ID-ul și încearcă din nou. ID: ' + (orderId || 'necunoscut') });
      });
  }

  check();
})();
