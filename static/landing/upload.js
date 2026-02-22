(function () {
  'use strict';

  var MAX_SIZE_MB = 10;
  var MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
  var data = window.STYLES_DATA || [];
  var params = new URLSearchParams(window.location.search);
  var styleId = params.get('style');
  var style = null;
  var photoFile = null;

  var styleCard = document.getElementById('style-card');
  var styleThumb = document.getElementById('style-thumb');
  var styleTag = document.getElementById('style-tag');
  var styleTitle = document.getElementById('style-title');
  var styleArtist = document.getElementById('style-artist');
  var styleDesc = document.getElementById('style-desc');
  var uploadZone = document.getElementById('upload-zone');
  var uploadZoneInner = document.getElementById('upload-zone-inner');
  var uploadPreview = document.getElementById('upload-preview');
  var photoInput = document.getElementById('photo-input');
  var previewImg = document.getElementById('preview-img');
  var uploadRemove = document.getElementById('upload-remove');
  var uploadSuccess = document.getElementById('upload-success');
  var uploadFilename = document.getElementById('upload-filename');
  var createBtn = document.getElementById('create-btn');
  var uploadError = document.getElementById('upload-error');
  var styleThumbPrev = document.getElementById('style-thumb-prev');
  var styleThumbNext = document.getElementById('style-thumb-next');

  function showError(msg) { if (uploadError) { uploadError.textContent = msg; uploadError.style.display = 'block'; } }
  function hideError() { if (uploadError) { uploadError.textContent = ''; uploadError.style.display = 'none'; } }

  function setPhoto(file) {
    photoFile = file;
    hideError();
    if (!file) {
      uploadZone.classList.remove('has-file');
      if (uploadPreview) uploadPreview.style.display = 'none';
      if (uploadZoneInner) uploadZoneInner.style.display = '';
      if (createBtn) createBtn.disabled = !style;
      if (photoInput) photoInput.value = '';
      return;
    }
    if (file.size > MAX_SIZE_BYTES) { showError('Fișierul trebuie să aibă maxim ' + MAX_SIZE_MB + ' MB.'); return; }
    var reader = new FileReader();
    reader.onload = function () {
      if (previewImg) previewImg.src = reader.result;
      if (uploadPreview) uploadPreview.style.display = 'flex';
      if (uploadZoneInner) uploadZoneInner.style.display = 'none';
      uploadZone.classList.add('has-file');
      if (uploadFilename) uploadFilename.textContent = file.name;
      if (uploadSuccess) uploadSuccess.style.display = 'none';
      if (createBtn) createBtn.disabled = false;
    };
    reader.readAsDataURL(file);
  }

  if (uploadZone) {
    uploadZone.addEventListener('dragover', function (e) { e.preventDefault(); uploadZone.classList.add('dragover'); });
    uploadZone.addEventListener('dragleave', function () { uploadZone.classList.remove('dragover'); });
    uploadZone.addEventListener('drop', function (e) {
      e.preventDefault();
      uploadZone.classList.remove('dragover');
      var file = e.dataTransfer.files[0];
      if (!file) return;
      if (file.type.indexOf('image/') !== 0) { showError('Adaugă o poză (JPG, PNG, WebP sau BMP).'); return; }
      setPhoto(file);
    });
  }
  if (photoInput) {
    photoInput.addEventListener('change', function () {
      var file = photoInput.files[0];
      if (!file) return;
      if (file.type.indexOf('image/') !== 0) {
        showError('Alege o poză (JPG, PNG, WebP sau BMP).');
        photoInput.value = '';
        return;
      }
      setPhoto(file);
    });
  }
  if (uploadRemove) {
    uploadRemove.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); setPhoto(null); });
  }

  if (createBtn) {
    createBtn.addEventListener('click', function () {
      if (!style) return;
      if (!photoFile) {
        showError('Adaugă mai întâi o poză.');
        if (uploadZone) {
          uploadZone.scrollIntoView({ behavior: 'smooth', block: 'center' });
          uploadZone.classList.add('upload-zone-pulse');
          setTimeout(function () { uploadZone.classList.remove('upload-zone-pulse'); }, 2000);
        }
        return;
      }
      hideError();
      createBtn.disabled = true;
      createBtn.textContent = 'Se continuă…';
      var formData = new FormData();
      formData.append('file', photoFile, photoFile.name || 'photo.jpg');
      fetch('/api/upload-image', { method: 'POST', body: formData })
        .then(function (r) { return r.json().catch(function () { return {}; }).then(function (d) { return { ok: r.ok, status: r.status, data: d }; }); })
        .then(function (res) {
          if (!res.ok) {
            var msg = (res.data && res.data.detail) ? res.data.detail : 'Upload failed.';
            throw new Error(msg);
          }
          var imageUrl = res.data && res.data.image_url;
          if (!imageUrl) throw new Error('Server did not return a photo URL.');
          window.location.href = '/details?style=' + encodeURIComponent(style.id) + '&image_url=' + encodeURIComponent(imageUrl);
        })
        .catch(function (err) {
          createBtn.disabled = false;
          createBtn.textContent = 'Continuă';
          showError(err && err.message ? err.message : 'Ceva nu a mers bine.');
        });
    });
  }

  // Load selected style
  if (styleId) {
    var id = parseInt(styleId, 10);
    style = data.find(function (s) { return s.id === id; });
  }
  if (!style) {
    if (styleCard) styleCard.innerHTML = '<p>Niciun stil ales. <a href="/styles">Alege un stil</a> mai întâi.</p>';
    if (createBtn) createBtn.disabled = true;
  } else {
    if (createBtn) createBtn.disabled = true;
    if (styleThumb) {
      var previewUrls = style.previewImageUrls && style.previewImageUrls.length > 0 ? style.previewImageUrls : (style.id === 13 ? ['/static/landing/styles/masters/masters-01.jpg', '/static/landing/styles/masters/masters-02.jpg', '/static/landing/styles/masters/masters-03.jpg', '/static/landing/styles/masters/masters-04.jpg', '/static/landing/styles/masters/masters-05.jpg'] : null);
      var useHorizontalScroll = previewUrls && previewUrls.length > 0;
      var useImage = (useHorizontalScroll || (style.styleImageUrl && style.styleImageUrl.length > 0));
      styleThumb.className = 'upload-style-thumb ' + (useHorizontalScroll ? 'upload-style-thumb-h-scroll' : (useImage ? 'upload-style-thumb-with-img' : (style.thumbnailClass || '')));
      styleThumb.style.backgroundImage = '';
      styleThumb.style.background = useImage ? '#f0ede8' : '';
      styleThumb.innerHTML = '';
      if (useHorizontalScroll) {
        previewUrls.forEach(function (url) {
          var thumbImg = document.createElement('img');
          thumbImg.src = url;
          thumbImg.alt = style.title || 'Style';
          thumbImg.setAttribute('aria-hidden', 'true');
          thumbImg.onerror = function () { this.style.display = 'none'; };
          styleThumb.appendChild(thumbImg);
        });
        if (styleThumbPrev) { styleThumbPrev.style.display = 'flex'; styleThumbPrev.onclick = function () { styleThumb.scrollBy({ left: -styleThumb.clientWidth, behavior: 'smooth' }); }; }
        if (styleThumbNext) { styleThumbNext.style.display = 'flex'; styleThumbNext.onclick = function () { styleThumb.scrollBy({ left: styleThumb.clientWidth, behavior: 'smooth' }); }; }
      } else {
        if (styleThumbPrev) styleThumbPrev.style.display = 'none';
        if (styleThumbNext) styleThumbNext.style.display = 'none';
      }
      if (!useHorizontalScroll && style.styleImageUrl) {
        var thumbImg = document.createElement('img');
        thumbImg.src = style.styleImageUrl;
        thumbImg.alt = style.title || 'Style';
        thumbImg.setAttribute('aria-hidden', 'true');
        thumbImg.onerror = function () { this.style.display = 'none'; };
        styleThumb.appendChild(thumbImg);
      }
    }
    if (styleTag) {
      styleTag.textContent = style.category;
      var catKey = style.category ? style.category.toLowerCase().replace(/[\s-]+/g, '') : '';
      styleTag.className = 'upload-style-tag tag-' + catKey;
    }
    if (styleTitle) styleTitle.textContent = style.title;
    if (styleArtist) styleArtist.textContent = style.artist;
    if (styleDesc) styleDesc.textContent = style.description || '';
  }
})();
