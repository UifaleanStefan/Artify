(function () {
  'use strict';

  function parseOrderId(value) {
    if (!value || typeof value !== 'string') return null;
    var s = value.trim();
    if (!s) return null;
    if (s.indexOf('ART-') === 0) return s;
    try {
      var url = new URL(s);
      var path = url.pathname || '';
      var m = path.match(/\/order\/([^/?#]+)/);
      return m ? m[1] : null;
    } catch (e) {
      return null;
    }
  }

  var input = document.getElementById('debug-input');
  var submit = document.getElementById('debug-submit');
  var errorEl = document.getElementById('debug-error');
  var output = document.getElementById('debug-output');
  var orderIdEl = document.getElementById('debug-order-id');
  var statusEl = document.getElementById('debug-status');
  var errorMsgEl = document.getElementById('debug-error-msg');
  var resultsSection = document.getElementById('debug-results-section');
  var resultCountEl = document.getElementById('debug-result-count');
  var gallery = document.getElementById('debug-gallery');
  var detailsSection = document.getElementById('debug-details-section');
  var detailsJson = document.getElementById('debug-details-json');

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.style.display = 'block';
  }
  function hideError() {
    errorEl.style.display = 'none';
    errorEl.textContent = '';
  }

  submit.addEventListener('click', function () {
    hideError();
    var raw = input.value;
    var orderId = parseOrderId(raw);
    if (!orderId) {
      showError('Please enter a valid order ID or order URL (e.g. https://.../order/ART-xxx).');
      output.style.display = 'none';
      return;
    }

    fetch('/api/orders/' + encodeURIComponent(orderId) + '/status')
      .then(function (r) {
        if (!r.ok) {
          if (r.status === 404) throw new Error('Order not found.');
          return r.json().then(function (d) { throw new Error(d.detail || d.message || 'Request failed'); });
        }
        return r.json();
      })
      .then(function (data) {
        output.style.display = 'block';
        orderIdEl.textContent = data.order_id || orderId;
        statusEl.textContent = 'Status: ' + (data.status || '—');
        statusEl.className = 'debug-status status-' + ((data.status || '').toLowerCase());

        errorMsgEl.style.display = 'none';
        if (data.error) {
          errorMsgEl.textContent = 'Error: ' + data.error;
          errorMsgEl.style.display = 'block';
        }

        var urls = [];
        if (data.result_urls) {
          try {
            urls = typeof data.result_urls === 'string' ? JSON.parse(data.result_urls) : (data.result_urls || []);
          } catch (e) {}
        }
        resultCountEl.textContent = urls.length;
        gallery.innerHTML = '';
        if (urls.length > 0) {
          resultsSection.style.display = 'block';
          urls.forEach(function (url, i) {
            var a = document.createElement('a');
            a.href = url;
            a.target = '_blank';
            a.rel = 'noopener';
            var img = document.createElement('img');
            img.src = url;
            img.alt = 'Result ' + (i + 1);
            a.appendChild(img);
            gallery.appendChild(a);
          });
        } else {
          resultsSection.style.display = 'none';
        }

        if (data.replicate_prediction_details) {
          detailsSection.style.display = 'block';
          var details = data.replicate_prediction_details;
          try {
            var str = typeof details === 'string' ? details : JSON.stringify(details, null, 2);
            detailsJson.textContent = str;
          } catch (e) {
            detailsJson.textContent = String(details);
          }
        } else {
          detailsSection.style.display = 'none';
        }
      })
      .catch(function (err) {
        showError(err.message || 'Failed to load order.');
        output.style.display = 'none';
      });
  });
})();
