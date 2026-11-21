document.addEventListener('DOMContentLoaded', async () => {
  const { escapeHTML, showToast } = window.UIUtils;

  const sessionSelect = document.getElementById('reportSessionSelect');
  let selectedId = new URLSearchParams(window.location.search).get('session_id');

  async function loadReport(sessionId) {
    if (!sessionId) return;
    try {
      const r = await window.ApiService.getCoachingReport(sessionId);
      document.getElementById('repReportId').textContent = r.report_id || 'REPORT';
      document.getElementById('repScore').textContent = `${r.evaluation_score}/100`;
      document.getElementById('repScoreBar').style.width = `${Math.min(100, Math.max(0, r.evaluation_score))}%`;
      document.getElementById('repSentiment').textContent = r.customer_sentiment || '—';
      document.getElementById('repSummary').textContent = r.conversation_summary || '—';
      document.getElementById('repEvalText').textContent = r.employee_evaluation || '—';

      document.getElementById('repStrengths').innerHTML =
        (r.strengths || []).map((item) => `<li>${escapeHTML(item)}</li>`).join('') || '<li>None listed.</li>';

      document.getElementById('repImprovements').innerHTML =
        (r.areas_for_improvement || []).map((item) => `<li>${escapeHTML(item)}</li>`).join('') || '<li>None listed.</li>';

      document.getElementById('repRecommendedReplies').innerHTML =
        (r.recommended_replies || []).map((reply) => `
          <div style="background:var(--blue-50); border:1px solid #bfdbfe; padding:12px 14px; border-radius:8px; font-size:0.9rem;">
            ${escapeHTML(reply)}
          </div>
        `).join('') || '<p class="helper-text">No recommended replies provided.</p>';
    } catch (err) {
      showToast(`Failed to load coaching report: ${err.message}`, 'error');
    }
  }

  document.getElementById('printReportBtn').addEventListener('click', () => window.print());
  sessionSelect.addEventListener('change', () => loadReport(sessionSelect.value));

  try {
    const sessions = await window.ApiService.getSessions();
    if (!sessions.length) return;
    sessionSelect.innerHTML = sessions.map((s) =>
      `<option value="${escapeHTML(s.session_id)}">${escapeHTML(s.session_id)} — ${escapeHTML(s.product_name)}</option>`
    ).join('');

    if (!selectedId || !sessions.some((s) => s.session_id === selectedId)) {
      selectedId = sessions[0].session_id;
    }
    sessionSelect.value = selectedId;
    await loadReport(selectedId);
  } catch (err) {
    showToast(`Could not load sessions: ${err.message}`, 'error');
  }
});