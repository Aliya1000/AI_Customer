(function (window, document) {
  'use strict';

  function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatDate(isoString) {
    if (!isoString) return '—';
    const d = new Date(isoString);
    if (Number.isNaN(d.getTime())) return isoString;
    return d.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  function showToast(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3800);
  }

  function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebarToggle');

    if (toggleBtn && sidebar) {
      toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('open');
      });
    }

    const rawPath = window.location.pathname.replace(/\/$/, '') || '/dashboard';
    const cleanCurrent = rawPath.replace(/\.html$/, '');
    document.querySelectorAll('.nav-link').forEach((link) => {
      const rawHref = link.getAttribute('href') || '';
      const cleanHref = rawHref.replace(/\.html$/, '').replace(/^\/?/, '/');
      if (cleanHref === cleanCurrent || (cleanCurrent === '' && cleanHref === '/dashboard')) {
        link.classList.add('active');
      }
    });

    const statusLabel = document.getElementById('apiModeLabel');
    const statusDot = document.getElementById('apiStatusDot');
    const modeBtn = document.getElementById('toggleApiModeBtn');

    function renderMode() {
      if (!statusLabel || !statusDot || !window.ApiService) return;
      statusLabel.textContent = `API: ${window.ApiService.config.BASE_URL}`;
      statusDot.className = 'status-dot live';
      if (modeBtn) modeBtn.textContent = 'Change API URL';
    }

    if (modeBtn && window.ApiService) {
      modeBtn.addEventListener('click', () => {
        const url = prompt('Enter Backend Base URL:', window.ApiService.config.BASE_URL);
        if (!url) return;
        window.ApiService.config.BASE_URL = url.trim();
        renderMode();
        showToast(`Connected to backend: ${window.ApiService.config.BASE_URL}`, 'info');
        setTimeout(() => window.location.reload(), 600);
      });
    }

    renderMode();
  }

  document.addEventListener('DOMContentLoaded', initSidebar);

  window.UIUtils = { escapeHTML, formatDate, showToast };
})(window, document);