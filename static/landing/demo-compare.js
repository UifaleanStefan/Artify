(function () {
  'use strict';
  var wraps = document.querySelectorAll('.compare-wrap');
  var minPct = 10;
  var maxPct = 90;

  function setPct(wrap, pct) {
    pct = Math.max(minPct, Math.min(maxPct, pct));
    wrap.style.setProperty('--compare-pct', String(pct));
  }

  function initSlider(wrap) {
    var divider = wrap.querySelector('.compare-divider');
    if (!divider) return;

    function onMove(e) {
      var rect = wrap.getBoundingClientRect();
      var x = e.clientX - rect.left;
      setPct(wrap, (x / rect.width) * 100);
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
        setPct(wrap, (x / rect.width) * 100);
      }
      function touchEnd() {
        wrap.removeEventListener('touchmove', touchMove);
        wrap.removeEventListener('touchend', touchEnd);
      }
      wrap.addEventListener('touchmove', touchMove, { passive: false });
      wrap.addEventListener('touchend', touchEnd);
      var rect = wrap.getBoundingClientRect();
      setPct(wrap, ((touch.clientX - rect.left) / rect.width) * 100);
    }, { passive: false });
  }

  wraps.forEach(initSlider);
})();
