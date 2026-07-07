// main.js -- small UX helpers shared across pages.

document.addEventListener('DOMContentLoaded', function () {
  // Auto-dismiss flashed alerts after a few seconds.
  document.querySelectorAll('.app-alert').forEach(function (alertEl) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
      bsAlert.close();
    }, 6000);
  });

  // Light / dark theme toggle. The actual theme attribute is set as early
  // as possible by an inline script in <head> (to avoid a flash of the
  // wrong theme); this just wires up the button and keeps its icon and
  // localStorage in sync with whatever theme is currently active.
  const root = document.documentElement;
  const toggleBtn = document.getElementById('themeToggle');
  const toggleIcon = document.getElementById('themeToggleIcon');

  function setIcon(theme) {
    if (!toggleIcon) return;
    toggleIcon.className = theme === 'light' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
  }

  setIcon(root.getAttribute('data-theme') || 'dark');

  if (toggleBtn) {
    toggleBtn.addEventListener('click', function () {
      const current = root.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
      const next = current === 'light' ? 'dark' : 'light';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('vt-theme', next); } catch (e) { /* private browsing, etc. */ }
      setIcon(next);
    });
  }
});
