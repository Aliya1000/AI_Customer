/**
 * API Service & Integration Layer
 * ------------------------------------------------------------
 * - Direct REST API integration with FastAPI backend.
 * - All database, storage, RAG & AI operations go through backend endpoints.
 * - No client-side mock data.
 */
(function (window) {
  'use strict';

  function normalizeBaseUrl(raw) {
    if (!raw) return '';
    return String(raw)
      .trim()
      .replace(/^["']+|["']+$/g, '')
      .replace(/\/+$/, '')
      .replace(/\/(docs|redoc|api)$/i, '');
  }

  const PRODUCTION_BACKEND_URL = 'https://ai-customer-backend-t3e5.onrender.com';
  const LEGACY_BACKEND_URLS = ['https://ai-customer-backend-sqq8.onrender.com'];

  const AppConfig = {
    get BASE_URL() {
      const saved = normalizeBaseUrl(localStorage.getItem('api_base_url'));
      if (saved && !LEGACY_BACKEND_URLS.includes(saved)) {
        return saved;
      }
      if (saved && LEGACY_BACKEND_URLS.includes(saved)) {
        localStorage.removeItem('api_base_url');
      }
      // If the page is served directly from the FastAPI backend on port 8000, use window.location.origin
      if (window.location.origin && window.location.port === '8000') {
        return window.location.origin;
      }
      // Production: connect GitHub Pages frontend to Render backend
      if (window.location.hostname === 'aliya1000.github.io') {
        return PRODUCTION_BACKEND_URL;
      }
      // Development default: static server (port 5500/3000/5173) or file:// -> target FastAPI at port 8000
      return 'http://localhost:8000';
    },
    set BASE_URL(val) {
      const clean = normalizeBaseUrl(val);
      if (clean) {
        localStorage.setItem('api_base_url', clean);
      }
    },
    get USE_MOCK() {
      return false;
    },
    set USE_MOCK(_) {
      // Mock mode deprecated
    }
  };

  async function httpRequest(endpoint, options = {}) {
    const url = `${AppConfig.BASE_URL.replace(/\/$/, '')}${endpoint}`;
    const config = { ...options };

    if (!(options.body instanceof FormData)) {
      config.headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      };
    }

    const res = await fetch(url, config);
    if (!res.ok) {
      const errBody = await res.text();
      throw new Error(`API ${res.status}: ${errBody || res.statusText}`);
    }
    return res.json();
  }

  const ApiService = {
    config: AppConfig,

    // 1. POST /api/sessions
    async createSession(payload) {
      return httpRequest('/api/sessions', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
    },

    // 2. GET /api/sessions
    async getSessions() {
      return httpRequest('/api/sessions');
    },

    // 3. GET /api/sessions/{id}
    async getSessionById(id) {
      return httpRequest(`/api/sessions/${encodeURIComponent(id)}`);
    },

    // 4. POST /api/sessions/{id}/messages
    async sendMessage(id, payload) {
      return httpRequest(`/api/sessions/${encodeURIComponent(id)}/messages`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });
    },

    // 5. GET /api/sessions/{id}/messages
    async getMessages(id) {
      return httpRequest(`/api/sessions/${encodeURIComponent(id)}/messages`);
    },

    // 6. POST /api/knowledge/upload
    async uploadKnowledgeDocument(formData) {
      return httpRequest('/api/knowledge/upload', {
        method: 'POST',
        body: formData
      });
    },

    // 7. GET /api/knowledge/documents
    async getKnowledgeDocuments() {
      return httpRequest('/api/knowledge/documents');
    },

    // 8. DELETE /api/knowledge/documents/{id}
    async deleteKnowledgeDocument(id) {
      return httpRequest(`/api/knowledge/documents/${encodeURIComponent(id)}`, {
        method: 'DELETE'
      });
    },

    // 9. GET /api/sessions/{id}/coaching-report
    async getCoachingReport(id) {
      return httpRequest(`/api/sessions/${encodeURIComponent(id)}/coaching-report`);
    },

    // 10. GET /api/products & POST /api/products
    async getProducts() {
      return httpRequest('/api/products');
    },

    async createProduct(payload) {
      return httpRequest('/api/products', {
        method: 'POST',
        body: JSON.stringify(payload)
      });
    },

    // 11. GET /api/analytics/trends
    async getAnalyticsTrends() {
      return httpRequest('/api/analytics/trends');
    },

    // 12. POST /api/sessions/{id}/diagnose-image (Multi-Modal Image Defect Analysis)
    async diagnoseImage(id, formData) {
      return httpRequest(`/api/sessions/${encodeURIComponent(id)}/diagnose-image`, {
        method: 'POST',
        body: formData
      });
    },

    // 13. SSE & WebSocket Streaming URL Helpers
    getStreamUrl(id) {
      return `${AppConfig.BASE_URL.replace(/\/$/, '')}/api/sessions/${encodeURIComponent(id)}/stream`;
    },

    getWebSocketUrl(id) {
      const wsProto = AppConfig.BASE_URL.startsWith('https') ? 'wss' : 'ws';
      const hostPart = AppConfig.BASE_URL.replace(/^https?:\/\//, '').replace(/\/$/, '');
      return `${wsProto}://${hostPart}/api/ws/sessions/${encodeURIComponent(id)}`;
    }
  };

  window.ApiService = ApiService;
})(window);
