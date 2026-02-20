(function () {
  'use strict';
  var data = window.STYLES_DATA || [];
  var params = new URLSearchParams(window.location.search);
  var styleId = params.get('style');
  var imageUrl = params.get('image_url');
  var email = params.get('email') || '';
  var style = null;

  if (styleId) { var id = parseInt(styleId, 10); style = data.find(function (s) { return s.id === id; }); }

  var thumb = document.getElementById('billing-thumb');
  var styleName = document.getElementById('billing-style-name');
  var styleArtist = document.getElementById('billing-style-artist');
  var emailEl = document.getElementById('billing-email');
  var backLink = document.getElementById('billing-back');

  if (style) {
    if (thumb) thumb.className = 'billing-summary-thumb ' + (style.thumbnailClass || '');
    if (styleName) styleName.textContent = style.title;
    if (styleArtist) styleArtist.textContent = style.artist;
  }
  if (emailEl) emailEl.textContent = email || '—';
  if (backLink) {
    var q = '?style=' + encodeURIComponent(styleId || '') + '&image_url=' + encodeURIComponent(imageUrl || '');
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
        if (errorEl) { errorEl.textContent = 'Please fill in all required fields.'; errorEl.style.display = 'block'; } return;
      }
      sessionStorage.setItem('billingInfo', JSON.stringify({ fullName: fullName, address1: address1, address2: address2, city: city, state: state, zip: zip, country: country }));
      var q = '?style=' + encodeURIComponent(styleId || '') + '&image_url=' + encodeURIComponent(imageUrl || '') + '&email=' + encodeURIComponent(email);
      window.location.href = '/payment' + q;
    });
  }
})();
