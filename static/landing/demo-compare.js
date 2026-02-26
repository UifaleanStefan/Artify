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

    /* Touch: drag handle to move slider; tap anywhere on image to jump */
    var handle = divider.querySelector('.compare-handle') || divider;

    handle.addEventListener('touchstart', function (e) {
      e.preventDefault(); /* stop outer scroll container stealing this drag */
      var touch = e.touches[0];
      var rect = wrap.getBoundingClientRect();
      setPct(wrap, ((touch.clientX - rect.left) / rect.width) * 100);

      function touchMove(ev) {
        ev.preventDefault();
        var t = ev.touches[0];
        var r = wrap.getBoundingClientRect();
        setPct(wrap, ((t.clientX - r.left) / r.width) * 100);
      }
      function touchEnd() {
        handle.removeEventListener('touchmove', touchMove);
        handle.removeEventListener('touchend', touchEnd);
      }
      handle.addEventListener('touchmove', touchMove, { passive: false });
      handle.addEventListener('touchend', touchEnd, { passive: true });
    }, { passive: false });

    /* Tap anywhere on the image (not on handle) to jump slider there */
    wrap.addEventListener('touchstart', function (e) {
      var touchedHandle = e.target === handle || handle.contains(e.target) ||
                          e.target === divider || divider.contains(e.target);
      if (touchedHandle) return; /* handled above */
      var touch = e.touches[0];
      var startX = touch.clientX;
      var startTime = Date.now();
      function touchEnd(ev) {
        wrap.removeEventListener('touchend', touchEnd);
        if (ev.changedTouches && Date.now() - startTime < 350 &&
            Math.abs(ev.changedTouches[0].clientX - startX) < 12) {
          moveToPosition(wrap, ev.changedTouches[0].clientX);
        }
      }
      wrap.addEventListener('touchend', touchEnd, { passive: true });
    }, { passive: true });
  }

  wraps.forEach(initSlider);
})();
