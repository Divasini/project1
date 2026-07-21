/* ============================================
   STARTUPSPHERE - script.js v2.0
   Theme Toggle + Scroll Reveal + Counters
   + Mobile Hamburger Menu
   ============================================ */

/* ── 1. THEME TOGGLE ─────────────────────────── */
function toggleTheme() {
  const body = document.body;
  const isDark = body.getAttribute('data-theme') !== 'light';
  const newTheme = isDark ? 'light' : 'dark';
  body.setAttribute('data-theme', newTheme);
  localStorage.setItem('ss-theme', newTheme);
  document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
    btn.textContent = newTheme === 'light' ? '☀️' : '🌙';
  });
}

(function () {
  const saved = localStorage.getItem('ss-theme') || 'dark';
  document.body.setAttribute('data-theme', saved);
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
      btn.textContent = saved === 'light' ? '☀️' : '🌙';
    });
  });
})();


/* ── 2. MOBILE HAMBURGER MENU ────────────────── */
function toggleMobileNav(btn) {
  const nav = document.getElementById('mobile-nav');
  if (!nav) return;
  nav.classList.toggle('open');
  btn.textContent = nav.classList.contains('open') ? '✕' : '☰';
}

document.addEventListener('DOMContentLoaded', () => {

  // Close nav when a link is tapped on mobile
  const mobileNav = document.getElementById('mobile-nav');
  if (mobileNav) {
    mobileNav.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        mobileNav.classList.remove('open');
        const btn = document.querySelector('.hamburger-btn');
        if (btn) btn.textContent = '☰';
      });
    });
  }

  // Close nav when tapping outside
  document.addEventListener('click', (e) => {
    const nav = document.getElementById('mobile-nav');
    const btn = document.querySelector('.hamburger-btn');
    if (nav && nav.classList.contains('open')) {
      if (!nav.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
        nav.classList.remove('open');
        btn.textContent = '☰';
      }
    }
  });


  /* ── 3. SCROLL REVEAL ──────────────────────── */
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const siblings = entry.target.parentElement.querySelectorAll('[data-reveal], .glass-card');
        let delay = 0;
        siblings.forEach((el, idx) => {
          if (el === entry.target) delay = idx * 80;
        });
        setTimeout(() => {
          entry.target.classList.add('visible');
        }, delay);
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.10 });

  document.querySelectorAll('.glass-card, [data-reveal]').forEach(el => {
    revealObserver.observe(el);
  });


  /* ── 4. COUNTER ANIMATION ──────────────────── */
  function animateCounter(el, target, duration = 1800) {
    let startTime = null;
    function step(timestamp) {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.floor(eased * target).toLocaleString();
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const counter = entry.target;
        if (counter.dataset.done) return;
        counter.dataset.done = '1';
        const target = parseInt(counter.dataset.target, 10);
        animateCounter(counter, target);
        counterObserver.unobserve(counter);
      }
    });
  }, { threshold: 0.4 });

  document.querySelectorAll('.counter[data-target]').forEach(el => {
    counterObserver.observe(el);
  });


  /* ── 5. CATEGORY CHIP FILTER ───────────────── */
  const chips = document.querySelectorAll('.category-chip');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
    });
  });


  /* ── 6. SEARCH FILTER (ideas.html) ─────────── */
  const searchInput = document.getElementById('search-input');
  const ideaCards   = document.querySelectorAll('.idea-card');

  if (searchInput && ideaCards.length) {
    searchInput.addEventListener('input', () => {
      const query = searchInput.value.toLowerCase();
      ideaCards.forEach(card => {
        const title = card.querySelector('h5')?.textContent.toLowerCase() || '';
        const desc  = card.querySelector('p')?.textContent.toLowerCase()  || '';
        card.closest('[class*="col"]').style.display =
          (title.includes(query) || desc.includes(query)) ? '' : 'none';
      });
    });
  }


  /* ── 7. NAVBAR ACTIVE LINK ──────────────────── */
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-menu a').forEach(link => {
    const href = link.getAttribute('href');
    if (href === currentPage) link.classList.add('active');
  });


  /* ── 8. NAVBAR AUTH STATE ───────────────────── */
  updateNavbarAuth();


  /* ── 9. FLOATING CONTACT BUTTON ─────────────── */
  addFloatingContactButton();


  /* ── 10. SMOOTH PAGE TRANSITION ────────────── */
  document.body.style.opacity = '0';
  document.body.style.transition = 'opacity 0.35s ease';
  setTimeout(() => { document.body.style.opacity = '1'; }, 30);

});


/* ── FLOATING CONTACT BUTTON ──────────────────────
   Adds a fixed bottom-right button that expands into
   quick contact options (WhatsApp, Email, Phone, Contact page).
================================================== */
function addFloatingContactButton() {
  // Don't add on the contact page itself
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  if (currentPage === 'contact.html') return;

  if (document.querySelector('.floating-contact-wrap')) return;

  const wrap = document.createElement('div');
  wrap.className = 'floating-contact-wrap';
  wrap.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:1000;display:flex;flex-direction:column;align-items:flex-end;gap:10px;';

  wrap.innerHTML = `
    <div class="floating-contact-menu" style="display:none;flex-direction:column;gap:10px;align-items:flex-end;">
      <a href="https://wa.me/916383898095" target="_blank" class="fc-item" style="display:flex;align-items:center;gap:10px;background:var(--bg2);border:1px solid var(--border);border-radius:30px;padding:10px 16px 10px 12px;font-size:13px;font-weight:600;color:var(--text);box-shadow:var(--shadow-lg);text-decoration:none;white-space:nowrap;">
        <span style="width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#10b981,#059669);display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;">💬</span> WhatsApp
      </a>
      <a href="mailto:startupsphere001@gmail.com" class="fc-item" style="display:flex;align-items:center;gap:10px;background:var(--bg2);border:1px solid var(--border);border-radius:30px;padding:10px 16px 10px 12px;font-size:13px;font-weight:600;color:var(--text);box-shadow:var(--shadow-lg);text-decoration:none;white-space:nowrap;">
        <span style="width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#6c63ff,#9b59f5);display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;">✉️</span> Email Us
      </a>
      <a href="tel:+916383898095" class="fc-item" style="display:flex;align-items:center;gap:10px;background:var(--bg2);border:1px solid var(--border);border-radius:30px;padding:10px 16px 10px 12px;font-size:13px;font-weight:600;color:var(--text);box-shadow:var(--shadow-lg);text-decoration:none;white-space:nowrap;">
        <span style="width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#00d4ff,#6c63ff);display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;">📞</span> Call Us
      </a>
      <a href="contact.html" class="fc-item" style="display:flex;align-items:center;gap:10px;background:var(--bg2);border:1px solid var(--border);border-radius:30px;padding:10px 16px 10px 12px;font-size:13px;font-weight:600;color:var(--text);box-shadow:var(--shadow-lg);text-decoration:none;white-space:nowrap;">
        <span style="width:30px;height:30px;border-radius:50%;background:var(--accent-grad);display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;">📋</span> Contact Page
      </a>
    </div>
    <button class="floating-contact-toggle" aria-label="Contact us" style="width:54px;height:54px;border-radius:50%;background:var(--accent-grad);border:none;color:#fff;font-size:22px;cursor:pointer;box-shadow:var(--shadow-lg);display:flex;align-items:center;justify-content:center;transition:all 0.3s var(--spring);">
      💬
    </button>
  `;

  document.body.appendChild(wrap);

  // Hover effect on menu items
  wrap.querySelectorAll('.fc-item').forEach(item => {
    item.addEventListener('mouseenter', () => {
      item.style.borderColor = 'var(--border2)';
      item.style.transform = 'translateX(-4px)';
      item.style.transition = 'all 0.25s';
    });
    item.addEventListener('mouseleave', () => {
      item.style.borderColor = 'var(--border)';
      item.style.transform = 'translateX(0)';
    });
  });

  // Toggle menu
  const toggleBtn = wrap.querySelector('.floating-contact-toggle');
  const menu = wrap.querySelector('.floating-contact-menu');
  let open = false;

  toggleBtn.addEventListener('click', () => {
    open = !open;
    menu.style.display = open ? 'flex' : 'none';
    toggleBtn.textContent = open ? '✕' : '💬';
    toggleBtn.style.transform = open ? 'rotate(90deg)' : 'rotate(0deg)';
  });

  // Close on outside click
  document.addEventListener('click', (e) => {
    if (open && !wrap.contains(e.target)) {
      open = false;
      menu.style.display = 'none';
      toggleBtn.textContent = '💬';
      toggleBtn.style.transform = 'rotate(0deg)';
    }
  });
}


/* ── NAVBAR AUTH STATE FUNCTION ──────────────────
   Replaces "Login / Get Started" with user avatar +
   name + Dashboard/Logout links when logged in.
   Call this on every page via script.js DOMContentLoaded.
================================================== */
function updateNavbarAuth() {
  const token   = localStorage.getItem('ss_token');
  const userStr = localStorage.getItem('ss_user');

  const navActions = document.querySelector('.nav-actions');
  if (!navActions) return;

  if (!token || !userStr) {
    return; // Not logged in — keep default Login/Get Started buttons
  }

  let user;
  try {
    user = JSON.parse(userStr);
  } catch (e) {
    return;
  }

  const loginBtn  = navActions.querySelector('.login-btn');
  const startBtn  = navActions.querySelector('a.btn-primary');

  if (loginBtn) loginBtn.style.display = 'none';
  if (startBtn) startBtn.style.display = 'none';

  // Avoid duplicating if already added
  if (navActions.querySelector('.user-menu-wrap')) return;

  const initials = user.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  const navApiBase = "http://localhost:8000";
  const avatarStyle = user.avatar_url
    ? `background-image:url('${navApiBase}${user.avatar_url}');background-size:cover;background-position:center;`
    : 'background:var(--accent-grad);';
  const avatarContent = user.avatar_url ? '' : initials;

  const wrap = document.createElement('div');
  wrap.className = 'user-menu-wrap';
  wrap.style.cssText = 'position:relative;display:flex;align-items:center;';

  wrap.innerHTML = `
    <button class="user-menu-btn" style="display:flex;align-items:center;gap:8px;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:6px 12px 6px 6px;cursor:pointer;color:var(--text);font-size:13px;font-weight:600;transition:all 0.25s;">
      <span style="width:28px;height:28px;border-radius:50%;${avatarStyle}display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;color:#fff;flex-shrink:0;">${avatarContent}</span>
      <span class="user-menu-name" style="max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHtmlNav(user.name)}</span>
      <span style="font-size:10px;color:var(--text3);">▾</span>
    </button>
    <div class="user-menu-dropdown" style="display:none;position:absolute;top:calc(100% + 8px);right:0;min-width:180px;background:var(--bg2);border:1px solid var(--border);border-radius:12px;box-shadow:var(--shadow-lg);overflow:hidden;z-index:1000;">
      <a href="profile.html" style="display:flex;align-items:center;gap:8px;padding:11px 16px;font-size:13px;color:var(--text2);transition:background 0.2s;">👤 My Profile</a>
      <a href="dashboard.html" style="display:flex;align-items:center;gap:8px;padding:11px 16px;font-size:13px;color:var(--text2);transition:background 0.2s;">📊 Dashboard</a>
      <a href="submit-idea.html" style="display:flex;align-items:center;gap:8px;padding:11px 16px;font-size:13px;color:var(--text2);transition:background 0.2s;">+ Submit Idea</a>
      <div style="border-top:1px solid var(--border);"></div>
      <button class="user-logout-btn" style="display:flex;align-items:center;gap:8px;padding:11px 16px;font-size:13px;color:#f87171;background:none;border:none;width:100%;text-align:left;cursor:pointer;transition:background 0.2s;">🚪 Logout</button>
    </div>
  `;

  // Insert before the theme toggle button (keep theme toggle visible)
  const themeBtn = navActions.querySelector('.theme-toggle-btn');
  if (themeBtn) {
    navActions.insertBefore(wrap, themeBtn);
  } else {
    navActions.appendChild(wrap);
  }

  // Hover styles for dropdown links
  wrap.querySelectorAll('.user-menu-dropdown a, .user-logout-btn').forEach(item => {
    item.addEventListener('mouseenter', () => { item.style.background = 'var(--card)'; item.style.color = 'var(--accent2)'; });
    item.addEventListener('mouseleave', () => { item.style.background = 'transparent'; item.style.color = item.classList.contains('user-logout-btn') ? '#f87171' : 'var(--text2)'; });
  });

  // Toggle dropdown
  const menuBtn = wrap.querySelector('.user-menu-btn');
  const dropdown = wrap.querySelector('.user-menu-dropdown');
  menuBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
  });

  // Close on outside click
  document.addEventListener('click', (e) => {
    if (!wrap.contains(e.target)) dropdown.style.display = 'none';
  });

  // Logout
  wrap.querySelector('.user-logout-btn').addEventListener('click', () => {
    localStorage.removeItem('ss_token');
    localStorage.removeItem('ss_user');
    window.location.href = 'login.html';
  });

  // ── Update hero "Get Started Free" / "Submit Idea" buttons if present ──
  document.querySelectorAll('a[href="signup.html"]').forEach(el => {
    if (el.closest('.nav-actions')) return; // already handled above
    el.href = 'dashboard.html';
    if (el.textContent.match(/get started/i)) {
      el.textContent = 'Go to Dashboard';
    }
  });
}

function escapeHtmlNav(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

/* ── USER SEARCH ICON (injected into navbar on every page) ── */
(function () {
  const API_BASE_SEARCH = "http://localhost:8000";

  document.addEventListener('DOMContentLoaded', () => {
    const navActions = document.querySelector('.nav-actions');
    if (!navActions) return;
    if (document.getElementById('user-search-wrap')) return;

    const token = localStorage.getItem('ss_token');
    if (!token) return; // Only show for logged-in users

    const wrap = document.createElement('div');
    wrap.id = 'user-search-wrap';
    wrap.style.cssText = 'position:relative;display:flex;align-items:center;';

    wrap.innerHTML = `
      <button id="user-search-btn" title="Find people" style="background:none;border:none;color:var(--text2);font-size:20px;cursor:pointer;display:flex;align-items:center;padding:0 6px;">
        <i class="fa-solid fa-magnifying-glass"></i>
      </button>
      <div id="user-search-panel" style="display:none;position:absolute;top:calc(100% + 10px);right:0;width:280px;background:var(--bg2);border:1px solid var(--border);border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,0.4);z-index:1000;padding:10px;">
        <input id="user-search-nav-input" placeholder="Search people..." style="width:100%;padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--card);color:var(--text);font-size:13px;outline:none;" autocomplete="off">
        <div id="user-search-nav-results" style="margin-top:8px;max-height:240px;overflow-y:auto;"></div>
      </div>
    `;

    // Insert before the messages icon if present, else append
    const msgIcon = navActions.querySelector('.messages-nav-icon');
    if (msgIcon) {
      navActions.insertBefore(wrap, msgIcon);
    } else {
      navActions.appendChild(wrap);
    }

    const btn = wrap.querySelector('#user-search-btn');
    const panel = wrap.querySelector('#user-search-panel');
    const input = wrap.querySelector('#user-search-nav-input');
    const results = wrap.querySelector('#user-search-nav-results');

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = panel.style.display === 'block';
      panel.style.display = isOpen ? 'none' : 'block';
      if (!isOpen) setTimeout(() => input.focus(), 50);
    });

    document.addEventListener('click', (e) => {
      if (!wrap.contains(e.target)) panel.style.display = 'none';
    });

    let debounceTimer = null;
    input.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      const q = this.value.trim();
      if (q.length < 2) {
        results.innerHTML = '';
        return;
      }
      debounceTimer = setTimeout(async () => {
        try {
          const res = await fetch(`${API_BASE_SEARCH}/users/search/query?q=${encodeURIComponent(q)}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          const users = await res.json();

          if (!res.ok || users.length === 0) {
            results.innerHTML = '<div style="padding:8px;font-size:12px;color:var(--text3);">No people found.</div>';
            return;
          }

          results.innerHTML = users.map(u => {
            const initials = u.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
            const avatarStyle = u.avatar_url
              ? `background-image:url('${API_BASE_SEARCH}${u.avatar_url}');background-size:cover;background-position:center;`
              : 'background:var(--accent-grad);';
            return `
              <a href="profile.html?id=${u.id}" style="display:flex;align-items:center;gap:8px;padding:8px;border-radius:8px;text-decoration:none;color:var(--text);" onmouseover="this.style.background='var(--card)'" onmouseout="this.style.background='none'">
                <span style="width:30px;height:30px;border-radius:50%;${avatarStyle}display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff;flex-shrink:0;">${u.avatar_url ? '' : initials}</span>
                <span style="font-size:13px;">${u.name}</span>
              </a>
            `;
          }).join('');

        } catch (err) {
          results.innerHTML = '<div style="padding:8px;font-size:12px;color:var(--text3);">Could not connect to server.</div>';
        }
      }, 350);
    });
  });
})();