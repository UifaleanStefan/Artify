(function () {
  'use strict';
  var navLinks = document.querySelectorAll('.nav a[href^="#"]');
  navLinks.forEach(function (link) {
    link.addEventListener('click', function (e) {
      var target = document.querySelector(link.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });

  var sections = document.querySelectorAll('section[id]');
  function onScroll() {
    var scrollY = window.scrollY + 100;
    sections.forEach(function (section) {
      var top = section.offsetTop;
      var h = section.offsetHeight;
      var id = section.getAttribute('id');
      var link = document.querySelector('.nav a[href="#' + id + '"]');
      if (link) {
        if (scrollY >= top && scrollY < top + h) {
          link.classList.add('active');
        } else {
          link.classList.remove('active');
        }
      }
    });
  }
  window.addEventListener('scroll', onScroll);

  /* Hamburger menu */
  var hamburgerBtn = document.getElementById('hamburger-btn');
  var menuOverlay = document.getElementById('menu-overlay');
  var menuClose = document.getElementById('menu-close');
  if (hamburgerBtn && menuOverlay && menuClose) {
    function openMenu() {
      menuOverlay.classList.add('open');
      menuOverlay.setAttribute('aria-hidden', 'false');
      hamburgerBtn.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
    }
    function closeMenu() {
      menuOverlay.classList.remove('open');
      menuOverlay.setAttribute('aria-hidden', 'true');
      hamburgerBtn.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    }
    hamburgerBtn.addEventListener('click', openMenu);
    menuClose.addEventListener('click', closeMenu);
    menuOverlay.addEventListener('click', function (e) {
      if (e.target === menuOverlay) closeMenu();
    });
    var menuLinks = menuOverlay.querySelectorAll('a');
    menuLinks.forEach(function (link) {
      link.addEventListener('click', function () { closeMenu(); });
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menuOverlay.classList.contains('open')) closeMenu();
    });
  }
})();
