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
  var refreshBtn = document.getElementById('debug-refresh-inline');
  var resumeBtn = document.getElementById('debug-resume-btn');

  var lastOrderId = null;

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
        lastOrderId = orderId;
        output.style.display = 'block';
        if (refreshBtn) refreshBtn.style.display = 'inline-flex';
        var status = (data.status || '').toLowerCase();
        if (resumeBtn) resumeBtn.style.display = status === 'processing' ? 'inline-flex' : 'none';
        orderIdEl.textContent = data.order_id || orderId;
        statusEl.textContent = 'Status: ' + (data.status || '—');
        statusEl.className = 'debug-status status-' + status;

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
        if (!Array.isArray(urls)) urls = [];
        if (urls.length === 0 && data.replicate_prediction_details) {
          var details = data.replicate_prediction_details;
          try {
            var arr = typeof details === 'string' ? JSON.parse(details) : details;
            if (Array.isArray(arr)) {
              arr.forEach(function (item) {
                if (item && item.result_url) urls.push(item.result_url);
              });
            }
          } catch (e2) {}
        }
        resultCountEl.textContent = urls.length;
        gallery.innerHTML = '';
        resultsSection.style.display = 'block';
        if (urls.length > 0) {
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
          var emptyMsg = document.createElement('p');
          emptyMsg.className = 'debug-no-images';
          emptyMsg.textContent = 'No result images yet (order may still be processing or no results stored).';
          gallery.appendChild(emptyMsg);
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

  if (refreshBtn) {
    refreshBtn.addEventListener('click', function () {
      if (lastOrderId) {
        input.value = lastOrderId;
        submit.click();
      }
    });
  }
  if (resumeBtn) {
    resumeBtn.addEventListener('click', function () {
      if (!lastOrderId) return;
      resumeBtn.disabled = true;
      resumeBtn.textContent = 'Resuming…';
      fetch('/api/debug/resume-order/' + encodeURIComponent(lastOrderId), { method: 'POST' })
        .then(function (r) {
          if (!r.ok) return r.json().then(function (d) { throw new Error(d.detail || d.message || 'Resume failed'); });
          return r.json();
        })
        .then(function () {
          resumeBtn.textContent = 'Resume queued – refresh in a minute';
          setTimeout(function () { submit.click(); }, 2000);
        })
        .catch(function (err) {
          resumeBtn.disabled = false;
          resumeBtn.textContent = 'Resume order (continue from last image)';
          showError(err.message || 'Resume failed');
        });
    });
  }
})();
