(function () {
  'use strict';

  var originalRow = document.getElementById('testimonial-cards-original');
  var duplicateRow = document.getElementById('testimonial-cards-duplicate');
  var trackH = document.getElementById('testimonial-track-h');
  var col1 = document.getElementById('testimonial-cards-col-1');
  var col2 = document.getElementById('testimonial-cards-col-2');

  if (!originalRow || !duplicateRow || !trackH || !col1 || !col2) return;

  var cards = originalRow.querySelectorAll('.testimonial-card');
  var cardArray = Array.prototype.slice.call(cards);

  function cloneCard(node) {
    return node.cloneNode(true);
  }

  // Horizontal: duplicate row for seamless loop
  cardArray.forEach(function (card) {
    duplicateRow.appendChild(cloneCard(card));
  });

  // Vertical treadmill: two identical columns
  cardArray.forEach(function (card) {
    col1.appendChild(cloneCard(card));
    col2.appendChild(cloneCard(card));
  });

  // Desktop: auto horizontal scroll (infinite loop)
  var scrollSpeed = 1;
  var scrollDelay = 18;
  var rowWidth = originalRow.offsetWidth;

  function scrollHorizontal() {
    if (!trackH || trackH.offsetParent === null) return; // hidden on mobile
    trackH.scrollLeft += scrollSpeed;
    if (trackH.scrollLeft >= rowWidth) {
      trackH.scrollLeft = 0;
    }
  }

  var horizontalInterval = setInterval(scrollHorizontal, scrollDelay);

  // Pause on hover (desktop)
  if (trackH) {
    trackH.addEventListener('mouseenter', function () {
      clearInterval(horizontalInterval);
    });
    trackH.addEventListener('mouseleave', function () {
      horizontalInterval = setInterval(scrollHorizontal, scrollDelay);
    });
  }
})();
