document.addEventListener('DOMContentLoaded', async () => {
  const { escapeHTML, formatDate, showToast } = window.UIUtils;

  const searchInput = document.getElementById('historySearch');
  const modeFilter = document.getElementById('historyModeFilter');
  const tableBody = document.getElementById('historyTableBody');

  let sessions = [];

  function render() {
    const q = searchInput.value.trim().toLowerCase();
    const mode = modeFilter.value;

    const filtered = sessions.filter((s) => {
      const matchMode = !mode || s.interaction_mode === mode;
      const matchText =
        !q ||
        s.session_id.toLowerCase().includes(q) ||
        s.product_name.toLowerCase().includes(q) ||
        s.customer_scenario.toLowerCase().includes(q);
      return matchMode && matchText;
    });

    if (!filtered.length) {
      tableBody.innerHTML = '<tr><td colspan="7">No matching sessions found.</td></tr>';
      return;
    }

    tableBody.innerHTML = filtered.map((s) => {
      const statusBadge = s.status === 'active' ? 'badge-warning' : 'badge-success';
      return `
        <tr>
          <td><strong>${escapeHTML(s.session_id)}</strong></td>
          <td><span class="badge badge-info">${escapeHTML(s.interaction_mode)}</span></td>
          <td>${escapeHTML(s.product_name)}</td>
          <td>${escapeHTML(s.customer_scenario.slice(0, 75))}${s.customer_scenario.length > 75 ? '...' : ''}</td>
          <td>${escapeHTML(formatDate(s.created_at))}</td>
          <td><span class="badge ${statusBadge}">${escapeHTML(s.status)}</span></td>
          <td style="display:flex; gap:6px;">
            <a class="btn btn-primary btn-sm" href="live-console.html?session_id=${encodeURIComponent(s.session_id)}">View Conversation</a>
            <a class="btn btn-secondary btn-sm" href="coaching-report.html?session_id=${encodeURIComponent(s.session_id)}">Report</a>
          </td>
        </tr>
      `;
    }).join('');
  }

  searchInput.addEventListener('input', render);
  modeFilter.addEventListener('change', render);

  try {
    sessions = await window.ApiService.getSessions();
    render();
  } catch (err) {
    showToast(`Failed to load session history: ${err.message}`, 'error');
  }
});