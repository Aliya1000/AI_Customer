document.addEventListener('DOMContentLoaded', async () => {
  const { escapeHTML, formatDate, showToast } = window.UIUtils;

  const sessionSelector = document.getElementById('sessionSelector');
  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatForm');
  const msgInput = document.getElementById('employeeMessageInput');
  const loadingBanner = document.getElementById('agentLoadingIndicator');
  const sendBtn = document.getElementById('sendMsgBtn');

  let activeSessionId = new URLSearchParams(window.location.search).get('session_id');
  let lastSuggestedReply = '';

  function renderMessages(messages) {
    document.getElementById('msgCountBadge').textContent = `${messages.length} msgs`;
    if (!messages.length) {
      chatMessages.innerHTML = '<p class="helper-text">No messages yet in this session.</p>';
      return;
    }
    chatMessages.innerHTML = messages.map((m) => {
      const isEmp = m.sender === 'employee';
      return `
        <div class="msg-bubble ${isEmp ? 'msg-employee' : 'msg-customer'}">
          <div>${escapeHTML(m.message_text)}</div>
          <div class="msg-meta">
            <span>${escapeHTML(m.sender.toUpperCase())}</span>
            <span>${escapeHTML(formatDate(m.timestamp))}</span>
          </div>
        </div>
      `;
    }).join('');
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function renderAgentOutputs(outputs) {
    if (!outputs) return;
    const supervisor = outputs.supervisor || {};
    const query_analysis = outputs.query_analysis || {};
    const knowledge_retrieval = outputs.knowledge_retrieval || {};
    const product_information = outputs.product_information || {};
    const response_generation = outputs.response_generation || {};
    const evaluation_and_coaching = outputs.evaluation_and_coaching || {};

    // 1. Supervisor
    document.getElementById('supStatus').textContent = supervisor.status || 'Completed';
    document.getElementById('supPattern').textContent = supervisor.active_pattern || 'Hybrid Orchestration';

    // 2. Query Analysis
    document.getElementById('qaIntent').textContent = query_analysis.intent || '—';
    document.getElementById('qaSentiment').textContent = query_analysis.sentiment || '—';
    document.getElementById('qaSummary').textContent = query_analysis.summary || '—';

    // 3. Knowledge Retrieval
    document.getElementById('krSummary').textContent = knowledge_retrieval.summary || '—';

    // 4. Product Info
    document.getElementById('piSummary').innerHTML = `
      <strong>${escapeHTML(product_information.product_name || '')}</strong><br/>
      <span>${escapeHTML(product_information.warranty_status || '')}</span>
    `;

    // 5. Response Generation
    lastSuggestedReply = response_generation.suggested_response || '';
    document.getElementById('rgSuggested').textContent = lastSuggestedReply || 'No suggestion available.';

    // 6. Evaluation & Coaching
    document.getElementById('ecScore').textContent = `${evaluation_and_coaching.evaluation_score ?? '—'}/100`;
    const tips = evaluation_and_coaching.tips || [];
    document.getElementById('ecTips').innerHTML = tips.map((t) => `<li>${escapeHTML(t)}</li>`).join('');

    // Right Panel
    document.getElementById('rightProductBox').innerHTML = `
      <strong>${escapeHTML(product_information.product_name || '')}</strong>
      <p class="kb-snippet" style="margin-top:4px;">${escapeHTML(product_information.product_description || '')}</p>
    `;

    const articles = knowledge_retrieval.articles || [];
    document.getElementById('rightArticlesList').innerHTML = articles.map((a) => `
      <div class="kb-item">
        <div class="kb-item-header">
          <span class="kb-item-title">${escapeHTML(a.title || '')}</span>
          <span class="badge badge-info">${Math.round((a.relevance_score || 0) * 100)}%</span>
        </div>
        <p class="kb-snippet">${escapeHTML(a.snippet || '')}</p>
        <small class="helper-text">Source: ${escapeHTML(a.source || '')}</small>
      </div>
    `).join('') || '<p class="helper-text">No KB articles retrieved.</p>';

    const steps = knowledge_retrieval.troubleshooting_steps || [];
    document.getElementById('rightTroubleshootingList').innerHTML = steps.map((s) => `<li>${escapeHTML(s)}</li>`).join('');

    const faqs = knowledge_retrieval.faqs || [];
    document.getElementById('rightFaqList').innerHTML = faqs.map((f) => `
      <div class="kb-item">
        <strong style="font-size:0.8rem;">Q: ${escapeHTML(f.question || '')}</strong>
        <p class="kb-snippet">A: ${escapeHTML(f.answer || '')}</p>
      </div>
    `).join('');
  }

  async function loadSession(sessionId) {
    if (!sessionId) return;
    activeSessionId = sessionId;
    try {
      const [session, messages] = await Promise.all([
        window.ApiService.getSessionById(sessionId),
        window.ApiService.getMessages(sessionId)
      ]);
      document.getElementById('bannerSessionId').textContent = session.session_id;
      document.getElementById('bannerMode').textContent = session.interaction_mode;
      document.getElementById('bannerProduct').textContent = session.product_name;
      document.getElementById('bannerPersona').textContent = session.persona;
      document.getElementById('viewReportLink').href = `coaching-report?session_id=${encodeURIComponent(session.session_id)}`;

      renderMessages(messages);
      renderAgentOutputs(session.agent_outputs);
    } catch (err) {
      showToast(`Failed to load session: ${err.message}`, 'error');
    }
  }

  document.getElementById('useSuggestedBtn').addEventListener('click', () => {
    if (lastSuggestedReply) {
      msgInput.value = lastSuggestedReply;
      msgInput.focus();
    }
  });

  async function handleSendMessage() {
    const text = msgInput.value.trim();
    if (!text) {
      showToast('Please type a message before sending.', 'warning');
      msgInput.focus();
      return;
    }

    try {
      sendBtn.disabled = true;
      loadingBanner.classList.remove('hidden');

      // Auto-create an active session if none is currently selected
      if (!activeSessionId) {
        showToast('Initializing new support session...', 'info');
        const newSession = await window.ApiService.createSession({
          interaction_mode: 'simulator',
          product_name: 'AeroSound Pro ANC Headphones',
          customer_scenario: text,
          persona: 'Angry'
        });
        activeSessionId = newSession.session_id;
        sessionSelector.innerHTML = `<option value="${newSession.session_id}">${newSession.session_id} — ${newSession.product_name}</option>`;
        sessionSelector.value = activeSessionId;
        document.getElementById('bannerSessionId').textContent = newSession.session_id;
        document.getElementById('bannerMode').textContent = newSession.interaction_mode;
        document.getElementById('bannerProduct').textContent = newSession.product_name;
        document.getElementById('bannerPersona').textContent = newSession.persona;
        document.getElementById('viewReportLink').href = `coaching-report?session_id=${encodeURIComponent(newSession.session_id)}`;
      }

      const sender = document.getElementById('senderRoleSelect').value || 'employee';

      const result = await window.ApiService.sendMessage(activeSessionId, {
        sender,
        message_text: text
      });

      msgInput.value = '';
      const updatedMessages = await window.ApiService.getMessages(activeSessionId);
      renderMessages(updatedMessages);
      renderAgentOutputs(result.agent_outputs);
    } catch (err) {
      showToast(`Message failed: ${err.message}`, 'error');
      console.error('Send message error:', err);
    } finally {
      sendBtn.disabled = false;
      loadingBanner.classList.add('hidden');
    }
  }

  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    handleSendMessage();
  });

  // Direct send button click listener
  sendBtn.addEventListener('click', (e) => {
    e.preventDefault();
    handleSendMessage();
  });

  // Send on Enter (allow Shift+Enter for new line)
  msgInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  sessionSelector.addEventListener('change', () => {
    if (sessionSelector.value) {
      loadSession(sessionSelector.value);
    }
  });

  try {
    const sessions = await window.ApiService.getSessions();
    if (!sessions || !sessions.length) {
      chatMessages.innerHTML = `
        <div style="text-align:center; padding: 28px 16px; color: var(--text-muted);">
          <p style="font-weight:600; margin-bottom:6px;">No Active Support Session</p>
          <p style="font-size:0.85rem; margin-bottom:14px;">Type your support message below to instantly launch a new session, or create one in Session Configuration.</p>
          <a href="session-config" class="btn btn-secondary btn-sm">Configure New Session</a>
        </div>
      `;
      sessionSelector.innerHTML = '<option value="">No sessions available</option>';
      return;
    }

    sessionSelector.innerHTML = sessions.map((s) =>
      `<option value="${escapeHTML(s.session_id)}">${escapeHTML(s.session_id)} — ${escapeHTML(s.product_name)}</option>`
    ).join('');

    if (!activeSessionId || !sessions.some((s) => s.session_id === activeSessionId)) {
      activeSessionId = sessions[0].session_id;
    }
    sessionSelector.value = activeSessionId;
    await loadSession(activeSessionId);
  } catch (err) {
    showToast(`Could not connect to backend: ${err.message}`, 'error');
    console.error('Init console error:', err);
    chatMessages.innerHTML = `
      <div style="text-align:center; padding: 28px 16px; color: var(--danger);">
        <p style="font-weight:600; margin-bottom:6px;">Backend Connection Error</p>
        <p style="font-size:0.85rem;">Make sure the FastAPI server is running on http://localhost:8000</p>
      </div>
    `;
  }
});