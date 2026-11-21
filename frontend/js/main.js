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

    const currentFile = window.location.pathname.split('/').pop() || 'dashboard.html';
    document.querySelectorAll('.nav-link').forEach((link) => {
      const href = link.getAttribute('href');
      if (href === currentFile || (currentFile === 'index.html' && href === 'dashboard.html')) {
        link.classList.add('active');
      }
    });

    const statusLabel = document.getElementById('apiModeLabel');
    const statusDot = document.getElementById('apiStatusDot');
    const modeBtn = document.getElementById('toggleApiModeBtn');

    function renderMode() {
      if (!statusLabel || !statusDot || !window.ApiService) return;
      const isMock = window.ApiService.config.USE_MOCK;
      statusLabel.textContent = isMock ? 'Mock Data Mode' : `Live: ${window.ApiService.config.BASE_URL}`;
      statusDot.className = `status-dot ${isMock ? 'mock' : 'live'}`;
      if (modeBtn) modeBtn.textContent = isMock ? 'Switch to Live API' : 'Switch to Mock';
    }

    if (modeBtn && window.ApiService) {
      modeBtn.addEventListener('click', () => {
        const nextMock = !window.ApiService.config.USE_MOCK;
        if (!nextMock) {
          const url = prompt('Enter Python Backend Base URL:', window.ApiService.config.BASE_URL);
          if (!url) return;
          window.ApiService.config.BASE_URL = url.trim();
        }
        window.ApiService.config.USE_MOCK = nextMock;
        renderMode();
        showToast(nextMock ? 'Switched to Mock Data mode' : 'Switched to Live Python API mode', 'info');
        setTimeout(() => window.location.reload(), 600);
      });
    }

    renderMode();
  }

  document.addEventListener('DOMContentLoaded', initSidebar);

  window.UIUtils = { escapeHTML, formatDate, showToast };
})(window, document);