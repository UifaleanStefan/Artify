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

  /* Header scroll fade: blend at top, solid on scroll */
  var mainHeader = document.getElementById('main-header');
  var heroSection = document.querySelector('.hero');
  if (mainHeader && mainHeader.classList.contains('header-scroll-fade')) {
    var SCROLL_THRESHOLD = 20;
    function updateHeaderScroll() {
      if (window.scrollY > SCROLL_THRESHOLD) {
        mainHeader.classList.add('header-scrolled');
        if (heroSection) heroSection.classList.add('hero--scrolled');
      } else {
        mainHeader.classList.remove('header-scrolled');
        if (heroSection) heroSection.classList.remove('hero--scrolled');
      }
    }
    updateHeaderScroll();
    window.addEventListener('scroll', updateHeaderScroll, { passive: true });
  }

  /* How-it-works: tap step number to highlight card on mobile */
  document.querySelectorAll('.how-step .step-number').forEach(function(num) {
    num.addEventListener('click', function() {
      var card = num.closest('.how-step').querySelector('.step-card');
      if (!card) return;
      card.classList.remove('step-card--flash');
      void card.offsetWidth; // reflow to restart animation
      card.classList.add('step-card--flash');
    });
  });

  /* Demo cards: auto-nudge on mobile to hint horizontal scroll */
  function nudgeScroll(el, distance, duration) {
    if (!el) return;
    var start = null;
    var startLeft = el.scrollLeft;
    function step(ts) {
      if (!start) start = ts;
      var progress = Math.min((ts - start) / duration, 1);
      // ease in-out
      var ease = progress < 0.5 ? 2 * progress * progress : -1 + (4 - 2 * progress) * progress;
      el.scrollLeft = startLeft + distance * ease;
      if (progress < 1) requestAnimationFrame(step);
      else {
        // scroll back
        var start2 = null;
        var fromLeft = el.scrollLeft;
        function stepBack(ts2) {
          if (!start2) start2 = ts2;
          var p2 = Math.min((ts2 - start2) / duration, 1);
          var e2 = p2 < 0.5 ? 2 * p2 * p2 : -1 + (4 - 2 * p2) * p2;
          el.scrollLeft = fromLeft - distance * e2;
          if (p2 < 1) requestAnimationFrame(stepBack);
        }
        requestAnimationFrame(stepBack);
      }
    }
    requestAnimationFrame(step);
  }

  function initDemoNudge() {
    var demoCards = document.querySelector('.demo-cards');
    if (!demoCards) return;
    // Only nudge on mobile (horizontal scroll layout)
    if (window.innerWidth > 900) return;
    // Use IntersectionObserver so nudge fires when section scrolls into view
    if ('IntersectionObserver' in window) {
      var nudgeDone = false;
      var obs = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
          if (entry.isIntersecting && !nudgeDone) {
            nudgeDone = true;
            setTimeout(function() { nudgeScroll(demoCards, 80, 500); }, 400);
            obs.disconnect();
          }
        });
      }, { threshold: 0.4 });
      obs.observe(demoCards);
    }
  }
  initDemoNudge();

  /* Hamburger menu */
  var hamburgerBtn = document.getElementById('hamburger-btn');
  var menuOverlay = document.getElementById('menu-overlay');
  var menuClose = document.getElementById('menu-close');
  var DESKTOP_BREAK = 769;

  function setMenuDesktopVisibility() {
    if (!menuOverlay) return;
    if (window.innerWidth >= DESKTOP_BREAK) {
      menuOverlay.style.display = 'none';
      menuOverlay.style.visibility = 'hidden';
      menuOverlay.classList.remove('open');
      document.body.style.overflow = '';
    } else {
      menuOverlay.style.display = '';
      menuOverlay.style.visibility = '';
    }
  }
  setMenuDesktopVisibility();
  window.addEventListener('resize', setMenuDesktopVisibility);

  if (hamburgerBtn && menuOverlay && menuClose) {
    function openMenu() {
      if (window.innerWidth >= DESKTOP_BREAK) return;
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
    window.addEventListener('resize', function () {
      if (window.innerWidth >= DESKTOP_BREAK && menuOverlay.classList.contains('open')) closeMenu();
    });
  }
})();
