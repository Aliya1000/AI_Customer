/**
 * API Service & Integration Layer
 * ------------------------------------------------------------
 * - All backend & SQL operations go through Python REST APIs.
 * - Never connect the browser directly to SQL.
 * - Toggle USE_MOCK to false once Python backend is running.
 */
(function (window) {
  'use strict';

  const STORAGE_KEY = 'ai_support_coaching_mock_db_v1';

  const AppConfig = {
    get BASE_URL() {
      return localStorage.getItem('api_base_url') || 'http://localhost:8000';
    },
    set BASE_URL(val) {
      localStorage.setItem('api_base_url', val);
    },
    get USE_MOCK() {
      const saved = localStorage.getItem('use_mock_data');
      return saved === null ? true : saved === 'true';
    },
    set USE_MOCK(val) {
      localStorage.setItem('use_mock_data', String(Boolean(val)));
    }
  };

  function getInitialMockDB() {
    return {
      products: [
        {
          product_id: 'PRD-01',
          product_name: 'AeroSound Pro ANC Headphones',
          product_description: 'Wireless Bluetooth 5.3 over-ear headphones with Hybrid Active Noise Cancellation and 1-year hardware warranty.',
          product_category: 'Audio Hardware'
        },
        {
          product_id: 'PRD-02',
          product_name: 'PulseWatch S4 Smartwatch',
          product_description: 'AMOLED fitness smartwatch with 5ATM water resistance and 10-day battery life.',
          product_category: 'Wearables'
        },
        {
          product_id: 'PRD-03',
          product_name: 'CloudDesk CRM Pro Subscription',
          product_description: 'Enterprise multi-seat SaaS subscription with SSO, API access, and 99.9% SLA.',
          product_category: 'SaaS Software'
        }
      ],
      sessions: [
        {
          session_id: 'SES-2026-0001',
          interaction_mode: 'simulator',
          product_name: 'AeroSound Pro ANC Headphones',
          product_context: 'Purchased 14 days ago. Covered under 30-day DOA & 1-year warranty.',
          customer_scenario: 'Customer reports cracked left earcup upon delivery and static noise when ANC is enabled.',
          persona: 'Angry',
          status: 'active',
          created_at: '2026-11-21T09:15:00Z'
        },
        {
          session_id: 'SES-2026-0002',
          interaction_mode: 'manual',
          product_name: 'PulseWatch S4 Smartwatch',
          product_context: 'Firmware v2.4 update released yesterday.',
          customer_scenario: 'Battery drains from 100% to 10% in 4 hours after firmware update.',
          persona: 'Confused',
          status: 'completed',
          created_at: '2026-11-20T16:40:00Z'
        },
        {
          session_id: 'SES-2026-0003',
          interaction_mode: 'replay',
          product_name: 'CloudDesk CRM Pro Subscription',
          product_context: 'Annual billing tier, 25 seats.',
          customer_scenario: 'Customer charged twice during seat upgrade.',
          persona: 'Impatient',
          status: 'completed',
          created_at: '2026-11-19T11:20:00Z'
        }
      ],
      messages: {
        'SES-2026-0001': [
          {
            message_id: 'MSG-001',
            session_id: 'SES-2026-0001',
            sender: 'customer',
            message_text: 'I just opened my AeroSound Pro headphones and the left earcup has a crack, plus the noise cancellation makes a loud buzzing sound! This is unacceptable.',
            timestamp: '2026-11-21T09:15:15Z'
          }
        ],
        'SES-2026-0002': [
          {
            message_id: 'MSG-002',
            session_id: 'SES-2026-0002',
            sender: 'customer',
            message_text: 'Hi, ever since I updated my PulseWatch S4 yesterday, the battery dies before lunch.',
            timestamp: '2026-11-20T16:40:20Z'
          },
          {
            message_id: 'MSG-003',
            session_id: 'SES-2026-0002',
            sender: 'employee',
            message_text: 'I understand how frustrating sudden battery drain is. Could you please perform a soft reset and disable Always-On Display temporarily while we push patch v2.4.1?',
            timestamp: '2026-11-20T16:42:05Z'
          }
        ],
        'SES-2026-0003': [
          {
            message_id: 'MSG-004',
            session_id: 'SES-2026-0003',
            sender: 'customer',
            message_text: 'You billed our company card twice when we added 5 seats!',
            timestamp: '2026-11-19T11:20:30Z'
          },
          {
            message_id: 'MSG-005',
            session_id: 'SES-2026-0003',
            sender: 'employee',
            message_text: 'I apologize for the duplicate charge. I have initiated a full refund for the second invoice, which will reflect in 3-5 business days.',
            timestamp: '2026-11-19T11:22:10Z'
          }
        ]
      },
      knowledgeDocuments: [
        {
          document_id: 'DOC-101',
          filename: 'aerosound_warranty_and_doa_policy.pdf',
          file_type: 'PDF',
          upload_time: '2026-11-15T10:00:00Z',
          processing_status: 'indexed'
        },
        {
          document_id: 'DOC-102',
          filename: 'pulsewatch_firmware_troubleshooting.txt',
          file_type: 'TXT',
          upload_time: '2026-11-18T14:25:00Z',
          processing_status: 'indexed'
        },
        {
          document_id: 'DOC-103',
          filename: 'billing_refund_sla_rules.json',
          file_type: 'JSON',
          upload_time: '2026-11-20T08:50:00Z',
          processing_status: 'processing'
        }
      ],
      coachingReports: {
        'SES-2026-0001': {
          report_id: 'REP-0001',
          session_id: 'SES-2026-0001',
          conversation_summary: '[MOCK] Customer reported physical damage (cracked earcup) and ANC static on newly delivered AeroSound Pro headphones.',
          customer_sentiment: 'Angry (High Escalation Risk)',
          evaluation_score: 84,
          employee_evaluation: '[MOCK] Pending final employee resolution turns. Initial tone should prioritize empathy and immediate DOA RMA dispatch.',
          strengths: ['Acknowledged product defect quickly', 'Correctly identified warranty coverage'],
          areas_for_improvement: ['Specify 48-hour express replacement SLA upfront', 'Request order photo in first reply to avoid extra back-and-forth'],
          recommendations: ['Use proactive DOA replacement script for damaged-in-transit hardware.'],
          recommended_replies: [
            'I sincerely apologize for receiving damaged AeroSound Pro headphones. Since this occurred on arrival, it qualifies for our 48-hour Express Replacement—please share your order number and a quick photo so I can ship a new unit today.'
          ]
        },
        'SES-2026-0002': {
          report_id: 'REP-0002',
          session_id: 'SES-2026-0002',
          conversation_summary: '[MOCK] Post-firmware battery drain reported on PulseWatch S4. Agent provided workaround and hotfix timeline.',
          customer_sentiment: 'Confused -> Reassured',
          evaluation_score: 91,
          employee_evaluation: '[MOCK] Clear, structured troubleshooting steps with empathetic tone.',
          strengths: ['Empathetic opening', 'Actionable workaround steps', 'Transparent about upcoming patch'],
          areas_for_improvement: ['Include link to firmware release notes'],
          recommendations: ['Follow up automatically once patch v2.4.1 goes live.'],
          recommended_replies: [
            'Thank you for reporting this. Firmware v2.4 has a known background sensor bug—performing a soft reset resolves it temporarily, and hotfix v2.4.1 rolls out tomorrow.'
          ]
        }
      }
    };
  }

  function loadMockDB() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      const init = getInitialMockDB();
      localStorage.setItem(STORAGE_KEY, JSON.stringify(init));
      return init;
    }
    return JSON.parse(raw);
  }

  function saveMockDB(db) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
  }

  function delay(ms = 400) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function buildMockAgentOutputs(session, latestText) {
    const productName = session ? session.product_name : 'Product';
    const isAngry = session && session.persona === 'Angry';
    const sampleText = latestText || (session ? session.customer_scenario : '');
    const hasEmpathy = /sorry|apologize|understand|glad to help/i.test(sampleText);

    return {
      supervisor: {
        status: 'Completed (Mock)',
        active_pattern: 'Hybrid: Supervisor -> Parallel(Query, RAG, Product) -> Sequential(Response, Evaluation)',
        agents_completed: 6
      },
      query_analysis: {
        summary: `[MOCK] Detected issue regarding ${productName}: "${sampleText.slice(0, 90)}..."`,
        intent: /refund|bill|charge/i.test(sampleText) ? 'Billing / Refund' : 'Hardware Defect / Replacement',
        sentiment: isAngry ? 'Frustrated / Urgent' : 'Concerned / Neutral'
      },
      knowledge_retrieval: {
        summary: `[MOCK] Retrieved 2 relevant RAG chunks for ${productName}.`,
        articles: [
          {
            title: `${productName} — Warranty & Replacement Guide`,
            source: 'aerosound_warranty_and_doa_policy.pdf',
            relevance_score: 0.94,
            snippet: 'Customers reporting physical defects or malfunction within 30 days qualify for prepaid RMA & express dispatch.'
          },
          {
            title: 'De-escalation & Empathy Playbook',
            source: 'support_coaching_handbook.txt',
            relevance_score: 0.87,
            snippet: 'Acknowledge the inconvenience explicitly before requesting verification details.'
          }
        ],
        faqs: [
          { question: 'Is return shipping covered?', answer: 'Yes, a prepaid label is generated automatically for DOA claims.' },
          { question: 'How fast is replacement delivery?', answer: 'Express replacement arrives within 2-3 business days.' }
        ],
        troubleshooting_steps: [
          'Acknowledge defect with empathy and verify Order ID.',
          'Request photo/error log if physical damage is reported.',
          'Trigger Express RMA workflow and share tracking ETA.'
        ]
      },
      product_information: {
        product_name: productName,
        product_category: 'Supported Catalog Item',
        product_description: session ? session.product_context : 'Standard product coverage.',
        warranty_status: 'Active — Eligible for Express Support'
      },
      response_generation: {
        suggested_response: `I completely understand how frustrating this issue with your ${productName} is, and I apologize for the inconvenience. Because your item is covered under warranty, I can arrange an immediate replacement—could you please confirm your order number so I can send your prepaid return label right away?`
      },
      evaluation_and_coaching: {
        evaluation_score: hasEmpathy ? 90 : 74,
        tips: hasEmpathy
          ? ['Strong empathetic opening.', 'Consider adding exact replacement SLA (2-3 business days).']
          : ['Start with a clear apology before asking questions.', 'Reference warranty coverage to reassure the customer.']
      }
    };
  }

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
      if (!AppConfig.USE_MOCK) {
        return httpRequest('/api/sessions', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
      }
      await delay(350);
      const db = loadMockDB();
      const newId = `SES-2026-${String(db.sessions.length + 1).padStart(4, '0')}`;
      const newSession = {
        session_id: newId,
        interaction_mode: payload.interaction_mode,
        product_name: payload.product_name,
        product_context: payload.product_context || '',
        customer_scenario: payload.customer_scenario,
        persona: payload.persona || 'Patient',
        status: 'active',
        created_at: new Date().toISOString()
      };
      db.sessions.unshift(newSession);
      db.messages[newId] = [
        {
          message_id: `MSG-${Date.now()}`,
          session_id: newId,
          sender: 'customer',
          message_text: payload.customer_scenario,
          timestamp: new Date().toISOString()
        }
      ];
      saveMockDB(db);
      return newSession;
    },

    // 2. GET /api/sessions
    async getSessions() {
      if (!AppConfig.USE_MOCK) {
        return httpRequest('/api/sessions');
      }
      await delay(200);
      return loadMockDB().sessions;
    },

    // 3. GET /api/sessions/{id}
    async getSessionById(id) {
      if (!AppConfig.USE_MOCK) {
        return httpRequest(`/api/sessions/${encodeURIComponent(id)}`);
      }
      await delay(200);
      const db = loadMockDB();
      const session = db.sessions.find((s) => s.session_id === id);
      if (!session) throw new Error(`Session ${id} not found`);
      const msgs = db.messages[id] || [];
      const latestText = msgs.length ? msgs[msgs.length - 1].message_text : session.customer_scenario;
      return {
        ...session,
        agent_outputs: buildMockAgentOutputs(session, latestText)
      };
    },

    // 4. POST /api/sessions/{id}/messages
    async sendMessage(id, payload) {
      if (!AppConfig.USE_MOCK) {
        return httpRequest(`/api/sessions/${encodeURIComponent(id)}/messages`, {
          method: 'POST',
          body: JSON.stringify(payload)
        });
      }
      await delay(650);
      const db = loadMockDB();
      const session = db.sessions.find((s) => s.session_id === id);
      if (!session) throw new Error(`Session ${id} not found`);

      const savedMsg = {
        message_id: `MSG-${Date.now()}`,
        session_id: id,
        sender: payload.sender || 'employee',
        message_text: payload.message_text,
        timestamp: new Date().toISOString()
      };
      db.messages[id] = db.messages[id] || [];
      db.messages[id].push(savedMsg);

      let simulatedReply = null;
      if (session.interaction_mode === 'simulator' && savedMsg.sender === 'employee') {
        simulatedReply = {
          message_id: `MSG-${Date.now() + 1}`,
          session_id: id,
          sender: 'customer',
          message_text: `[MOCK ${session.persona} Persona] Thanks for replying. My order ID is #ORD-88412—how soon can you fix this?`,
          timestamp: new Date(Date.now() + 1000).toISOString()
        };
        db.messages[id].push(simulatedReply);
      }

      saveMockDB(db);
      return {
        saved_message: savedMsg,
        simulated_customer_reply: simulatedReply,
        agent_outputs: buildMockAgentOutputs(session, savedMsg.message_text)
      };
    },

    // 5. GET /api/sessions/{id}/messages
    async getMessages(id) {
      if (!AppConfig.USE_MOCK) {
        return httpRequest(`/api/sessions/${encodeURIComponent(id)}/messages`);
      }
      await delay(150);
      const db = loadMockDB();
      return db.messages[id] || [];
    },

    // 6. POST /api/knowledge/upload
    async uploadKnowledgeDocument(formData) {
      if (!AppConfig.USE_MOCK) {
        return httpRequest('/api/knowledge/upload', {
          method: 'POST',
          body: formData
        });
      }
      await delay(500);
      const file = formData.get('file');
      const ext = file.name.split('.').pop().toUpperCase();
      const db = loadMockDB();
      const doc = {
        document_id: `DOC-${Date.now().toString().slice(-4)}`,
        filename: file.name,
        file_type: ext,
        upload_time: new Date().toISOString(),
        processing_status: 'indexed'
      };
      db.knowledgeDocuments.unshift(doc);
      saveMockDB(db);
      return doc;
    },

    // 7. GET /api/knowledge/documents
    async getKnowledgeDocuments() {
      if (!AppConfig.USE_MOCK) {
        return httpRequest('/api/knowledge/documents');
      }
      await delay(200);
      return loadMockDB().knowledgeDocuments;
    },

    // 8. DELETE /api/knowledge/documents/{id}
    async deleteKnowledgeDocument(id) {
      if (!AppConfig.USE_MOCK) {
        return httpRequest(`/api/knowledge/documents/${encodeURIComponent(id)}`, {
          method: 'DELETE'
        });
      }
      await delay(250);
      const db = loadMockDB();
      db.knowledgeDocuments = db.knowledgeDocuments.filter((d) => d.document_id !== id);
      saveMockDB(db);
      return { deleted: true, document_id: id };
    },

    // 9. GET /api/sessions/{id}/coaching-report
    async getCoachingReport(id) {
      if (!AppConfig.USE_MOCK) {
        return httpRequest(`/api/sessions/${encodeURIComponent(id)}/coaching-report`);
      }
      await delay(300);
      const db = loadMockDB();
      if (db.coachingReports[id]) {
        return db.coachingReports[id];
      }
      const session = db.sessions.find((s) => s.session_id === id);
      if (!session) throw new Error(`Session ${id} not found`);
      return {
        report_id: `REP-${id.slice(-4)}`,
        session_id: id,
        conversation_summary: `[MOCK] Support session for ${session.product_name}: ${session.customer_scenario}`,
        customer_sentiment: `${session.persona} -> Neutral`,
        evaluation_score: 85,
        employee_evaluation: '[MOCK] Good adherence to support guidelines. Awaiting final Python Evaluation Agent scoring.',
        strengths: ['Prompt acknowledgment', 'Clear product identification'],
        areas_for_improvement: ['Include proactive next steps and timeline'],
        recommendations: ['Confirm customer satisfaction before closing ticket.'],
        recommended_replies: [
          `Thank you for reaching out regarding your ${session.product_name}. I am resolving this right away and will share confirmation within 15 minutes.`
        ]
      };
    },

    async getProducts() {
      if (!AppConfig.USE_MOCK) {
        return httpRequest('/api/products');
      }
      return loadMockDB().products;
    }
  };

  window.ApiService = ApiService;
})(window);