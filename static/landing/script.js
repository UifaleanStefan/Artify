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

  /* Header scroll fade: transparent at top, frosted once scrolled */
  var mainHeader = document.getElementById('main-header');
  if (mainHeader && mainHeader.classList.contains('header-scroll-fade')) {
    var SCROLL_THRESHOLD = 40;
    function updateHeaderScroll() {
      mainHeader.classList.toggle('header-scrolled', window.scrollY > SCROLL_THRESHOLD);
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

  /* Demo cards: auto-sweep slider on mobile to show how comparison works */
  function sweepSlider(wrap, fromPct, toPct, duration, onDone) {
    var start = null;
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / duration, 1);
      var ease = p < 0.5 ? 2 * p * p : -1 + (4 - 2 * p) * p;
      var pct = fromPct + (toPct - fromPct) * ease;
      wrap.style.setProperty('--compare-pct', String(pct));
      if (p < 1) requestAnimationFrame(step);
      else if (onDone) onDone();
    }
    requestAnimationFrame(step);
  }

  function autoAnimateCompare(wrap) {
    // Start at 50%, sweep to 20% (show artistic), then to 80% (show original), back to 50%
    wrap.style.setProperty('--compare-pct', '50');
    setTimeout(function() {
      sweepSlider(wrap, 50, 20, 900, function() {
        setTimeout(function() {
          sweepSlider(wrap, 20, 80, 1400, function() {
            setTimeout(function() {
              sweepSlider(wrap, 80, 50, 700);
            }, 400);
          });
        }, 300);
      });
    }, 500);
  }

  function initDemoAutoAnimate() {
    if (window.innerWidth > 900) return; // desktop users drag manually
    var wraps = document.querySelectorAll('.compare-wrap');
    if (!wraps.length) return;
    if ('IntersectionObserver' in window) {
      wraps.forEach(function(wrap) {
        var animated = false;
        var obs = new IntersectionObserver(function(entries) {
          entries.forEach(function(entry) {
            if (entry.isIntersecting && !animated) {
              animated = true;
              autoAnimateCompare(wrap);
              obs.unobserve(wrap);
            }
          });
        }, { threshold: 0.5 });
        obs.observe(wrap);
      });
    }
  }
  initDemoAutoAnimate();

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
