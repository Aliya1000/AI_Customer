document.addEventListener('DOMContentLoaded', async () => {
  const { escapeHTML, showToast } = window.UIUtils;

  function drawSatisfactionChart(trendPoints) {
    const canvas = document.getElementById('satisfactionChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    const w = rect.width;
    const h = rect.height;
    const pad = { top: 20, right: 20, bottom: 32, left: 38 };
    const chartW = w - pad.left - pad.right;
    const chartH = h - pad.top - pad.bottom;

    ctx.clearRect(0, 0, w, h);

    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1;
    ctx.font = '11px sans-serif';
    ctx.fillStyle = '#64748b';
    [60, 75, 90, 100].forEach((val) => {
      const y = pad.top + chartH - ((val - 50) / 50) * chartH;
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(w - pad.right, y);
      ctx.stroke();
      ctx.fillText(`${val}%`, 4, y + 4);
    });

    if (!trendPoints || trendPoints.length === 0) {
      ctx.font = '13px sans-serif';
      ctx.fillStyle = '#94a3b8';
      ctx.textAlign = 'center';
      ctx.fillText('No conversation data recorded yet', w / 2, h / 2);
      ctx.textAlign = 'left';
      return;
    }

    const labels = trendPoints.map(p => p.day || p.date || '');
    const values = trendPoints.map(p => p.satisfaction_rate || p.score || 0);

    const pts = values.map((v, i) => ({
      x: pad.left + (trendPoints.length === 1 ? chartW / 2 : (i / (values.length - 1)) * chartW),
      y: pad.top + chartH - (Math.max(0, Math.min(50, v - 50)) / 50) * chartH
    }));

    ctx.beginPath();
    ctx.moveTo(pts[0].x, pad.top + chartH);
    pts.forEach((p) => ctx.lineTo(p.x, p.y));
    ctx.lineTo(pts[pts.length - 1].x, pad.top + chartH);
    ctx.closePath();
    ctx.fillStyle = 'rgba(37, 99, 235, 0.12)';
    ctx.fill();

    ctx.beginPath();
    pts.forEach((p, i) => (i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y)));
    ctx.strokeStyle = '#2563eb';
    ctx.lineWidth = 2.5;
    ctx.stroke();

    pts.forEach((p, i) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#0b1e38';
      ctx.fill();
      ctx.fillStyle = '#475569';
      ctx.fillText(labels[i], p.x - 10, h - 10);
    });
  }

  async function loadDashboard() {
    try {
      const sessions = await window.ApiService.getSessions();
      const activeCount = sessions.filter((s) => s.status === 'active').length;
      const completedCount = sessions.filter((s) => s.status === 'completed').length;

      document.getElementById('kpiTotal').textContent = sessions.length;
      document.getElementById('kpiActive').textContent = activeCount;
      document.getElementById('kpiCompleted').textContent = completedCount;

      try {
        const trends = await window.ApiService.getAnalyticsTrends();
        if (trends && trends.daily_satisfaction_trends) {
          drawSatisfactionChart(trends.daily_satisfaction_trends);
        } else {
          drawSatisfactionChart([]);
        }
      } catch (err) {
        drawSatisfactionChart([]);
      }

      const tbody = document.getElementById('recentSessionsBody');
      if (!sessions.length) {
        tbody.innerHTML = '<tr><td colspan="6">No conversations found. Start a new session!</td></tr>';
        return;
      }

      tbody.innerHTML = sessions.slice(0, 5).map((s) => {
        const badgeClass = s.status === 'active' ? 'badge-warning' : 'badge-success';
        return `
          <tr>
            <td><strong>${escapeHTML(s.session_id)}</strong></td>
            <td><span class="badge badge-info">${escapeHTML(s.interaction_mode)}</span></td>
            <td>${escapeHTML(s.product_name)}</td>
            <td>${escapeHTML(s.customer_scenario.slice(0, 65))}${s.customer_scenario.length > 65 ? '...' : ''}</td>
            <td><span class="badge ${badgeClass}">${escapeHTML(s.status)}</span></td>
            <td>
              <a class="btn btn-secondary btn-sm" href="live-console?session_id=${encodeURIComponent(s.session_id)}">Open Console</a>
            </td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      showToast(`Failed to load dashboard: ${err.message}`, 'error');
    }
  }

  drawSatisfactionChart();
  window.addEventListener('resize', drawSatisfactionChart);
  loadDashboard();
});