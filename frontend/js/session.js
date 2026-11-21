document.addEventListener('DOMContentLoaded', async () => {
  const { showToast } = window.UIUtils;

  const form = document.getElementById('sessionConfigForm');
  const modeSelect = document.getElementById('interactionMode');
  const productInput = document.getElementById('productName');
  const contextInput = document.getElementById('productContext');
  const scenarioInput = document.getElementById('customerScenario');
  const presetSelect = document.getElementById('scenarioPreset');
  const replayFileInput = document.getElementById('replayFile');
  const manualBtn = document.getElementById('submitManualProblemBtn');
  const startBtn = document.getElementById('startSessionBtn');
  const loadingEl = document.getElementById('sessionLoading');

  let replayContent = null;

  try {
    const products = await window.ApiService.getProducts();
    const list = document.getElementById('productSuggestions');
    list.innerHTML = products.map((p) => `<option value="${p.product_name}"></option>`).join('');
  } catch (_) {}

  function updateModeVisibility() {
    const mode = modeSelect.value;
    document.querySelectorAll('.mode-panel').forEach((panel) => {
      panel.classList.toggle('hidden', panel.dataset.mode !== mode);
    });
    manualBtn.classList.toggle('hidden', mode !== 'manual');
    document.getElementById('scenarioLabel').innerHTML =
      mode === 'manual'
        ? 'Customer Complaint <span class="required">*</span>'
        : 'Customer Problem / Scenario <span class="required">*</span>';
  }

  modeSelect.addEventListener('change', updateModeVisibility);
  updateModeVisibility();

  presetSelect.addEventListener('change', () => {
    if (presetSelect.value) {
      scenarioInput.value = presetSelect.value;
    }
  });

  replayFileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    document.getElementById('errReplay').textContent = '';
    if (!file) {
      replayContent = null;
      return;
    }
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['txt', 'json'].includes(ext)) {
      document.getElementById('errReplay').textContent = 'Only .txt and .json files are supported.';
      replayFileInput.value = '';
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      replayContent = reader.result;
      document.getElementById('replayFileInfo').textContent = `Loaded: ${file.name} (${file.size} bytes)`;
      if (!scenarioInput.value.trim()) {
        scenarioInput.value = `Replay transcript imported from ${file.name}`;
      }
    };
    reader.readAsText(file);
  });

  function validateForm() {
    let valid = true;
    ['errMode', 'errProduct', 'errContext', 'errScenario', 'errReplay'].forEach((id) => {
      document.getElementById(id).textContent = '';
    });

    if (!productInput.value.trim()) {
      document.getElementById('errProduct').textContent = 'Product name is required.';
      valid = false;
    }
    if (!contextInput.value.trim()) {
      document.getElementById('errContext').textContent = 'Product context is required.';
      valid = false;
    }
    if (!scenarioInput.value.trim()) {
      document.getElementById('errScenario').textContent = 'Customer problem/scenario is required.';
      valid = false;
    }
    if (modeSelect.value === 'replay' && !replayContent) {
      document.getElementById('errReplay').textContent = 'Please upload a TXT or JSON transcript.';
      valid = false;
    }
    return valid;
  }

  async function handleSubmit() {
    if (!validateForm()) return;

    const payload = {
      interaction_mode: modeSelect.value,
      product_name: productInput.value.trim(),
      product_context: contextInput.value.trim(),
      customer_scenario: scenarioInput.value.trim(),
      persona: modeSelect.value === 'simulator' ? document.getElementById('customerPersona').value : 'Standard',
      emotional_progression: modeSelect.value === 'simulator' ? document.getElementById('emotionalProgression').value : null,
      replay_transcript: modeSelect.value === 'replay' ? replayContent : null
    };

    try {
      startBtn.disabled = true;
      loadingEl.classList.remove('hidden');
      const created = await window.ApiService.createSession(payload);

      document.getElementById('generatedSessionId').textContent = created.session_id;
      document.getElementById('launchConsoleLink').href = `live-console.html?session_id=${encodeURIComponent(created.session_id)}`;
      document.getElementById('sessionCreatedBox').classList.remove('hidden');
      showToast(`Session ${created.session_id} created!`, 'success');
    } catch (err) {
      showToast(`Error creating session: ${err.message}`, 'error');
    } finally {
      startBtn.disabled = false;
      loadingEl.classList.add('hidden');
    }
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    handleSubmit();
  });

  manualBtn.addEventListener('click', handleSubmit);
});