(function () {
  'use strict';
  var data = window.STYLES_DATA || [];
  var params = new URLSearchParams(window.location.search);
  var styleId = params.get('style');
  var imageUrl = params.get('image_url');
  var portraitMode = params.get('portrait_mode') || 'realistic';
  var email = params.get('email') || '';
  var style = null;

  if (styleId) { var id = parseInt(styleId, 10); style = data.find(function (s) { return s.id === id; }); }

  var thumb = document.getElementById('billing-thumb');
  var styleName = document.getElementById('billing-style-name');
  var styleArtist = document.getElementById('billing-style-artist');
  var emailEl = document.getElementById('billing-email');
  var backLink = document.getElementById('billing-back');
  var thumbPrev = document.getElementById('billing-thumb-prev');
  var thumbNext = document.getElementById('billing-thumb-next');

  function fillPackThumb(el, s, prevBtn, nextBtn) {
    var isMasters = Number(s.id) === 13;
    var mastersUrls = ['/static/landing/styles/masters/masters-01.jpg', '/static/landing/styles/masters/masters-02.jpg', '/static/landing/styles/masters/masters-03.jpg', '/static/landing/styles/masters/masters-04.jpg', '/static/landing/styles/masters/masters-05.jpg'];
    var previewUrls = (s.previewImageUrls && s.previewImageUrls.length) ? s.previewImageUrls : (isMasters ? mastersUrls : null);
    if (previewUrls && previewUrls.length) {
      el.className = 'billing-summary-thumb style-thumb-h-scroll';
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
      el.className = 'billing-summary-thumb style-thumb-single';
      el.innerHTML = '<img src="' + s.styleImageUrl + '" alt="' + (s.title || 'Style') + '" />';
      if (prevBtn) prevBtn.style.display = 'none';
      if (nextBtn) nextBtn.style.display = 'none';
    } else {
      el.className = 'billing-summary-thumb ' + (s.thumbnailClass || '');
      el.innerHTML = '';
      if (prevBtn) prevBtn.style.display = 'none';
      if (nextBtn) nextBtn.style.display = 'none';
    }
  }

  if (style) {
    if (thumb) fillPackThumb(thumb, style, thumbPrev, thumbNext);
    if (styleName) styleName.textContent = style.title;
    if (styleArtist) styleArtist.textContent = style.artist;
  }
  if (emailEl) emailEl.textContent = email || '—';
  if (backLink) {
    var q = '?style=' + encodeURIComponent(styleId || '') + '&image_url=' + encodeURIComponent(imageUrl || '') + '&portrait_mode=' + encodeURIComponent(portraitMode);
    backLink.href = '/details' + q;
  }

  var form = document.getElementById('billing-form');
  var errorEl = document.getElementById('billing-form-error');

  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (errorEl) { errorEl.style.display = 'none'; }
      var fullName = document.getElementById('full-name').value.trim();
      var address1 = document.getElementById('address1').value.trim();
      var address2 = (document.getElementById('address2').value || '').trim();
      var city = document.getElementById('city').value.trim();
      var state = (document.getElementById('state').value || '').trim();
      var zip = document.getElementById('zip').value.trim();
      var country = document.getElementById('country').value.trim();
      if (!fullName || !address1 || !city || !zip || !country) {
        if (errorEl) { errorEl.textContent = 'Completează toate câmpurile obligatorii.'; errorEl.style.display = 'block'; } return;
      }
      sessionStorage.setItem('billingInfo', JSON.stringify({ fullName: fullName, address1: address1, address2: address2, city: city, state: state, zip: zip, country: country }));
      var q = '?style=' + encodeURIComponent(styleId || '') + '&image_url=' + encodeURIComponent(imageUrl || '') + '&portrait_mode=' + encodeURIComponent(portraitMode) + '&email=' + encodeURIComponent(email);
      window.location.href = '/payment' + q;
    });
  }
})();
