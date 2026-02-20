(function () {
  'use strict';
  var data = window.STYLES_DATA || [];
  var params = new URLSearchParams(window.location.search);
  var styleId = params.get('style');
  var imageUrl = params.get('image_url');
  var style = null;

  if (styleId) { var id = parseInt(styleId, 10); style = data.find(function (s) { return s.id === id; }); }

  var thumb = document.getElementById('details-style-thumb');
  var title = document.getElementById('details-style-title');
  var artist = document.getElementById('details-style-artist');
  var photoPreview = document.getElementById('details-photo-preview');
  var backLink = document.getElementById('details-back');

  if (style) {
    if (thumb) thumb.className = 'details-style-thumb ' + (style.thumbnailClass || '');
    if (title) title.textContent = style.title;
    if (artist) artist.textContent = style.artist;
  }
  if (imageUrl && photoPreview) {
    photoPreview.innerHTML = '<img src="' + imageUrl + '" alt="Your photo" />';
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
      if (!email) { if (errorEl) { errorEl.textContent = 'Email is required.'; errorEl.style.display = 'block'; } return; }
      if (email !== confirm) { if (errorEl) { errorEl.textContent = 'Emails do not match.'; errorEl.style.display = 'block'; } return; }
      var q = '?style=' + encodeURIComponent(styleId || '') + '&image_url=' + encodeURIComponent(imageUrl || '') + '&email=' + encodeURIComponent(email);
      window.location.href = '/billing' + q;
    });
  }
})();
