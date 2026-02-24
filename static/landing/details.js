(function () {
  'use strict';
  var data = window.STYLES_DATA || [];
  var params = new URLSearchParams(window.location.search);
  var styleId = params.get('style');
  var imageUrl = params.get('image_url');
  var portraitMode = params.get('portrait_mode') || 'realistic';
  var style = null;

  if (styleId) { var id = parseInt(styleId, 10); style = data.find(function (s) { return s.id === id; }); }

  var thumb = document.getElementById('details-style-thumb');
  var title = document.getElementById('details-style-title');
  var artist = document.getElementById('details-style-artist');
  var photoPreview = document.getElementById('details-photo-preview');
  var backLink = document.getElementById('details-back');
  var thumbPrev = document.getElementById('details-thumb-prev');
  var thumbNext = document.getElementById('details-thumb-next');

  function fillPackThumb(el, s, prevBtn, nextBtn) {
    var isMasters = Number(s.id) === 13;
    var mastersUrls = ['/static/landing/styles/masters/masters-01.jpg', '/static/landing/styles/masters/masters-02.jpg', '/static/landing/styles/masters/masters-03.jpg', '/static/landing/styles/masters/masters-04.jpg', '/static/landing/styles/masters/masters-05.jpg'];
    var previewUrls = (s.previewImageUrls && s.previewImageUrls.length) ? s.previewImageUrls : (isMasters ? mastersUrls : null);
    if (previewUrls && previewUrls.length) {
      el.className = 'details-style-thumb style-thumb-h-scroll';
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
      el.className = 'details-style-thumb style-thumb-single';
      el.innerHTML = '<img src="' + s.styleImageUrl + '" alt="' + (s.title || 'Style') + '" />';
      if (prevBtn) prevBtn.style.display = 'none';
      if (nextBtn) nextBtn.style.display = 'none';
    } else {
      el.className = 'details-style-thumb ' + (s.thumbnailClass || '');
      el.innerHTML = '';
      if (prevBtn) prevBtn.style.display = 'none';
      if (nextBtn) nextBtn.style.display = 'none';
    }
  }

  if (style) {
    if (thumb) fillPackThumb(thumb, style, thumbPrev, thumbNext);
    if (title) title.textContent = style.title;
    if (artist) artist.textContent = style.artist;
  }
  if (imageUrl && photoPreview) {
    photoPreview.innerHTML = '<img src="' + imageUrl + '" alt="Poză ta" />';
  }
  if (backLink) { backLink.href = '/upload?style=' + encodeURIComponent(styleId || ''); }

  var form = document.getElementById('details-form');
  var errorEl = document.getElementById('details-form-error');

  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var email = (document.getElementById('email').value || '').trim();
      var confirm = (document.getElementById('email-confirm').value || '').trim();
      if (errorEl) { errorEl.style.display = 'none'; errorEl.textContent = ''; }
      if (!email) { if (errorEl) { errorEl.textContent = 'Adresa de email este obligatorie.'; errorEl.style.display = 'block'; } return; }
      if (email !== confirm) { if (errorEl) { errorEl.textContent = 'Adresele de email nu coincid.'; errorEl.style.display = 'block'; } return; }
      var q = '?style=' + encodeURIComponent(styleId || '') + '&image_url=' + encodeURIComponent(imageUrl || '') + '&portrait_mode=' + encodeURIComponent(portraitMode) + '&email=' + encodeURIComponent(email);
      window.location.href = '/billing' + q;
    });
  }
})();
