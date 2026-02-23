(function () {
  'use strict';
  var data = window.STYLES_DATA || [];
  var grid = document.getElementById('styles-grid');
  var emptyMsg = document.getElementById('styles-empty');
  var searchInput = document.getElementById('styles-search');
  var filtersWrap = document.getElementById('styles-filters');
  var activeCategory = 'all';

  function tagClass(cat) {
    var map = {
      'Impressionism': 'tag-impressionism',
      'Renaissance': 'tag-renaissance',
      'Modern': 'tag-modern',
      'Pop Art': 'tag-popart',
      'Surrealism': 'tag-surrealism',
      'Post-Impressionism': 'tag-postimpressionism',
      'Ukiyo-e': 'tag-ukiyoe',
      'Baroque': 'tag-baroque',
      'Fauvism': 'tag-fauvism',
      'Masters': 'tag-masters',
      'Ancient': 'tag-ancient',
    };
    return map[cat] || 'tag-impressionism';
  }

  function thumbStyle(s) {
    if (s.preview && s.styleImageUrl) return 'background-image:url(' + s.styleImageUrl + ')';
    return '';
  }

  function renderCards(styles) {
    if (!grid) return;
    grid.innerHTML = '';
    if (styles.length === 0) {
      if (emptyMsg) emptyMsg.style.display = 'block';
      return;
    }
    if (emptyMsg) emptyMsg.style.display = 'none';

    styles.forEach(function (s) {
      var card = document.createElement('a');
      card.className = 'gallery-card';
      card.href = '/upload?style=' + s.id;
      card.innerHTML =
        '<div class="gallery-card-thumb">' +
          '<div class="gallery-card-thumb-bg ' + (s.preview && s.styleImageUrl ? '' : (s.thumbnailClass || '')) + '"' + (s.preview && s.styleImageUrl ? ' style="' + thumbStyle(s) + '"' : '') + '></div>' +
          '<span class="gallery-card-tag ' + tagClass(s.category) + '">' + s.category + '</span>' +
        '</div>' +
        '<div class="gallery-card-body">' +
          '<h3>' + s.title + '</h3>' +
          '<p class="gallery-card-artist">' + s.artist + '</p>' +
          '<p class="gallery-card-desc">' + s.description + '</p>' +
          '<div class="gallery-card-footer">' +
            '<span class="gallery-card-rating">★ ' + s.rating + '</span>' +
            '<span class="gallery-card-select">Alege stilul →</span>' +
          '</div>' +
        '</div>';
      grid.appendChild(card);
    });
  }

  function filterAndRender() {
    var query = (searchInput ? searchInput.value : '').toLowerCase().trim();
    var filtered = data.filter(function (s) {
      var catMatch = activeCategory === 'all' || s.category === activeCategory;
      if (!catMatch) return false;
      if (!query) return true;
      return (
        s.title.toLowerCase().indexOf(query) >= 0 ||
        s.artist.toLowerCase().indexOf(query) >= 0 ||
        s.category.toLowerCase().indexOf(query) >= 0 ||
        s.description.toLowerCase().indexOf(query) >= 0
      );
    });
    renderCards(filtered);
  }

  if (searchInput) {
    searchInput.addEventListener('input', filterAndRender);
  }

  if (filtersWrap) {
    filtersWrap.addEventListener('click', function (e) {
      var btn = e.target.closest('.filter-btn');
      if (!btn) return;
      filtersWrap.querySelectorAll('.filter-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      activeCategory = btn.getAttribute('data-cat') || 'all';
      filterAndRender();
    });
  }

  filterAndRender();
})();
