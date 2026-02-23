(function () {
  'use strict';

  var track = document.getElementById('style-cards-track');
  var originalRow = document.getElementById('style-cards-original');
  var duplicateRow = document.getElementById('style-cards-duplicate');

  if (!track || !originalRow || !duplicateRow) return;

  var cards = originalRow.querySelectorAll('.style-card');
  Array.prototype.forEach.call(cards, function (card) {
    duplicateRow.appendChild(card.cloneNode(true));
  });

  var scrollSpeed = 1.5;
  var scrollDelay = 16;
  var rowWidth = originalRow.offsetWidth;

  function scrollStyleCards() {
    if (!track || track.offsetParent === null || rowWidth <= 0) return;
    track.scrollLeft += scrollSpeed;
    if (track.scrollLeft >= rowWidth) {
      track.scrollLeft = 0;
    }
  }

  var scrollInterval = setInterval(scrollStyleCards, scrollDelay);

  track.addEventListener('mouseenter', function () {
    clearInterval(scrollInterval);
  });
  track.addEventListener('mouseleave', function () {
    scrollInterval = setInterval(scrollStyleCards, scrollDelay);
  });
})();
