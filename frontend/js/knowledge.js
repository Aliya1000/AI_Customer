document.addEventListener('DOMContentLoaded', () => {
  const { escapeHTML, formatDate, showToast } = window.UIUtils;

  const uploadForm = document.getElementById('kbUploadForm');
  const fileInput = document.getElementById('kbFileInput');
  const searchInput = document.getElementById('kbSearchInput');
  const tableBody = document.getElementById('kbTableBody');
  const uploadBtn = document.getElementById('uploadDocBtn');

  let allDocs = [];

  function statusBadge(status) {
    if (status === 'indexed') return 'badge-success';
    if (status === 'processing' || status === 'pending') return 'badge-warning';
    return 'badge-danger';
  }

  function renderDocs(docs) {
    if (!docs.length) {
      tableBody.innerHTML = '<tr><td colspan="6">No documents match your filter.</td></tr>';
      return;
    }
    tableBody.innerHTML = docs.map((d) => `
      <tr>
        <td><strong>${escapeHTML(d.document_id)}</strong></td>
        <td>${escapeHTML(d.filename)}</td>
        <td><span class="badge badge-info">${escapeHTML(d.file_type)}</span></td>
        <td>${escapeHTML(formatDate(d.upload_time))}</td>
        <td><span class="badge ${statusBadge(d.processing_status)}">${escapeHTML(d.processing_status)}</span></td>
        <td>
          <button type="button" class="btn btn-danger btn-sm delete-doc-btn" data-id="${escapeHTML(d.document_id)}">Delete</button>
        </td>
      </tr>
    `).join('');
  }

  async function loadDocuments() {
    try {
      allDocs = await window.ApiService.getKnowledgeDocuments();
      filterAndRender();
    } catch (err) {
      showToast(`Failed to fetch documents: ${err.message}`, 'error');
    }
  }

  function filterAndRender() {
    const q = searchInput.value.trim().toLowerCase();
    const filtered = q ? allDocs.filter((d) => d.filename.toLowerCase().includes(q)) : allDocs;
    renderDocs(filtered);
  }

  searchInput.addEventListener('input', filterAndRender);

  uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const file = fileInput.files[0];
    if (!file) return;
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'txt', 'json'].includes(ext)) {
      showToast('Invalid file type. Only PDF, TXT, and JSON are allowed.', 'error');
      return;
    }
    const formData = new FormData();
    formData.append('file', file);

    try {
      uploadBtn.disabled = true;
      uploadBtn.textContent = 'Uploading...';
      await window.ApiService.uploadKnowledgeDocument(formData);
      fileInput.value = '';
      showToast(`${file.name} uploaded successfully.`, 'success');
      await loadDocuments();
    } catch (err) {
      showToast(`Upload failed: ${err.message}`, 'error');
    } finally {
      uploadBtn.disabled = false;
      uploadBtn.textContent = 'Upload Document';
    }
  });

  tableBody.addEventListener('click', async (e) => {
    const btn = e.target.closest('.delete-doc-btn');
    if (!btn) return;
    const id = btn.dataset.id;
    if (!confirm(`Delete document ${id} from knowledge base?`)) return;

    try {
      await window.ApiService.deleteKnowledgeDocument(id);
      showToast(`Document ${id} deleted.`, 'success');
      await loadDocuments();
    } catch (err) {
      showToast(`Delete failed: ${err.message}`, 'error');
    }
  });

  loadDocuments();
});