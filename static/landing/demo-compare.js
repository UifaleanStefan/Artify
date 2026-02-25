(function () {
  'use strict';
  var wraps = document.querySelectorAll('.compare-wrap');
  var minPct = 10;
  var maxPct = 90;

  function setPct(wrap, pct) {
    pct = Math.max(minPct, Math.min(maxPct, pct));
    wrap.style.setProperty('--compare-pct', String(pct));
  }

  function moveToPosition(wrap, clientX) {
    var rect = wrap.getBoundingClientRect();
    var x = clientX - rect.left;
    setPct(wrap, (x / rect.width) * 100);
  }

  function initSlider(wrap) {
    var divider = wrap.querySelector('.compare-divider');
    if (!divider) return;

    var isDragging = false;

    function onMove(e) {
      var rect = wrap.getBoundingClientRect();
      var x = e.clientX - rect.left;
      setPct(wrap, (x / rect.width) * 100);
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
      moveToPosition(wrap, e.clientX);
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
        setPct(wrap, ((t.clientX - rect.left) / rect.width) * 100);
      }
      function touchEnd(ev) {
        wrap.removeEventListener('touchmove', touchMove);
        wrap.removeEventListener('touchend', touchEnd);
        /* If short tap with little movement, move slider to tap position */
        if (!moved && ev.changedTouches && ev.changedTouches[0] && Date.now() - startTime < 400) {
          var endX = ev.changedTouches[0].clientX;
          if (Math.abs(endX - startX) < 15) {
            moveToPosition(wrap, ev.changedTouches[0].clientX);
          }
        }
      }

      if (touchedDivider) {
        e.preventDefault();
        var rect = wrap.getBoundingClientRect();
        setPct(wrap, ((touch.clientX - rect.left) / rect.width) * 100);
      }
      wrap.addEventListener('touchmove', touchMove, { passive: false });
      wrap.addEventListener('touchend', touchEnd, { passive: true });
    }, { passive: true });
  }

  wraps.forEach(initSlider);
})();
