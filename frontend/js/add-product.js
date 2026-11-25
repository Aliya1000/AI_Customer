document.addEventListener('DOMContentLoaded', () => {
  const { escapeHTML, showToast } = window.UIUtils;

  const form = document.getElementById('addProductForm');
  const nameInput = document.getElementById('newProductName');
  const categorySelect = document.getElementById('newProductCategory');
  const customCategoryGroup = document.getElementById('customCategoryGroup');
  const customCategoryInput = document.getElementById('customProductCategory');
  const descriptionInput = document.getElementById('newProductDescription');
  const docsInput = document.getElementById('productDocsInput');
  const docsInfo = document.getElementById('selectedDocsInfo');
  const submitBtn = document.getElementById('submitProductBtn');
  const loadingEl = document.getElementById('addProductLoading');
  const createdBox = document.getElementById('productCreatedBox');
  const createdSummary = document.getElementById('productCreatedSummary');
  const useInSessionLink = document.getElementById('useInSessionLink');
  const productsTableBody = document.getElementById('productsTableBody');
  const productCountBadge = document.getElementById('productCountBadge');

  const ALLOWED_EXTENSIONS = [
    'pdf',
    'docx',
    'doc',
    'png',
    'jpg',
    'jpeg',
    'webp',
    'bmp',
    'txt',
    'md',
    'markdown',
    'json'
  ];
  const DEFAULT_DOCS_HELPER =
    'Upload one or more manuals, Word docs, images/diagrams, Markdown, TXT, or JSON files (.pdf, .docx, .doc, .png, .jpg, .jpeg, .webp, .bmp, .txt, .md, .markdown, .json).';

  categorySelect.addEventListener('change', () => {
    const isOther = categorySelect.value === 'Other';
    customCategoryGroup.classList.toggle('hidden', !isOther);
    if (!isOther) {
      customCategoryInput.value = '';
      document.getElementById('errCustomCategory').textContent = '';
    }
  });

  docsInput.addEventListener('change', () => {
    document.getElementById('errProdDocs').textContent = '';
    const files = Array.from(docsInput.files || []);
    if (!files.length) {
      docsInfo.textContent = DEFAULT_DOCS_HELPER;
      return;
    }
    const invalid = files.filter((f) => !ALLOWED_EXTENSIONS.includes(f.name.split('.').pop().toLowerCase()));
    if (invalid.length) {
      document.getElementById('errProdDocs').textContent = `Unsupported file(s): ${invalid.map((f) => f.name).join(', ')}. Allowed: PDF, DOCX, DOC, PNG, JPG, JPEG, WEBP, BMP, TXT, MD, MARKDOWN, JSON.`;
      docsInput.value = '';
      docsInfo.textContent = DEFAULT_DOCS_HELPER;
      return;
    }
    const names = files.map((f) => `${f.name} (${Math.max(1, Math.round(f.size / 1024))} KB)`).join(', ');
    docsInfo.textContent = `Selected ${files.length} document(s): ${names}`;
  });

  async function loadProducts() {
    try {
      const products = await window.ApiService.getProducts();
      productCountBadge.textContent = `${products.length} product${products.length === 1 ? '' : 's'}`;
      if (!products.length) {
        productsTableBody.innerHTML = '<tr><td colspan="4">No products registered yet.</td></tr>';
        return;
      }
      productsTableBody.innerHTML = products.map((p) => `
        <tr>
          <td><strong>${escapeHTML(p.product_id)}</strong></td>
          <td>${escapeHTML(p.product_name)}</td>
          <td><span class="badge badge-info">${escapeHTML(p.product_category)}</span></td>
          <td>${escapeHTML(p.product_description)}</td>
        </tr>
      `).join('');
    } catch (err) {
      productsTableBody.innerHTML = '<tr><td colspan="4">Unable to load products.</td></tr>';
      showToast(`Failed to load products: ${err.message}`, 'error');
    }
  }

  function validateForm() {
    let valid = true;
    ['errProdName', 'errProdCategory', 'errCustomCategory', 'errProdDescription', 'errProdDocs'].forEach((id) => {
      document.getElementById(id).textContent = '';
    });

    if (!nameInput.value.trim()) {
      document.getElementById('errProdName').textContent = 'Product name is required.';
      valid = false;
    }

    if (!categorySelect.value) {
      document.getElementById('errProdCategory').textContent = 'Please select a product category.';
      valid = false;
    } else if (categorySelect.value === 'Other' && !customCategoryInput.value.trim()) {
      document.getElementById('errCustomCategory').textContent = 'Please enter a custom category.';
      valid = false;
    }

    if (!descriptionInput.value.trim()) {
      document.getElementById('errProdDescription').textContent = 'Product description is required.';
      valid = false;
    }

    const files = Array.from(docsInput.files || []);
    if (!files.length) {
      document.getElementById('errProdDocs').textContent = 'At least one knowledge document is required.';
      valid = false;
    } else {
      const invalid = files.filter((f) => !ALLOWED_EXTENSIONS.includes(f.name.split('.').pop().toLowerCase()));
      if (invalid.length) {
        document.getElementById('errProdDocs').textContent = 'Allowed formats: PDF, DOCX, DOC, PNG, JPG, JPEG, WEBP, BMP, TXT, MD, MARKDOWN, JSON.';
        valid = false;
      }
    }

    return valid;
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    const category = categorySelect.value === 'Other'
      ? customCategoryInput.value.trim()
      : categorySelect.value;

    const productPayload = {
      product_name: nameInput.value.trim(),
      product_category: category,
      product_description: descriptionInput.value.trim()
    };

    const files = Array.from(docsInput.files || []);

    try {
      submitBtn.disabled = true;
      loadingEl.classList.remove('hidden');
      createdBox.classList.add('hidden');

      const createdProduct = await window.ApiService.createProduct(productPayload);

      const uploadedDocs = [];
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        const docRes = await window.ApiService.uploadKnowledgeDocument(formData);
        uploadedDocs.push(docRes.filename || file.name);
      }

      createdSummary.innerHTML = `
        Product <strong>${escapeHTML(createdProduct.product_name)}</strong> (${escapeHTML(createdProduct.product_id)}) created under
        <strong>${escapeHTML(createdProduct.product_category)}</strong>, and <strong>${uploadedDocs.length}</strong> document(s)
        (${escapeHTML(uploadedDocs.join(', '))}) sent to the knowledge base via the RAG pipeline.
      `;
      useInSessionLink.href = `session-config?product=${encodeURIComponent(createdProduct.product_name)}`;
      createdBox.classList.remove('hidden');

      form.reset();
      customCategoryGroup.classList.add('hidden');
      docsInfo.textContent = DEFAULT_DOCS_HELPER;
      showToast(`Product "${createdProduct.product_name}" added and ${uploadedDocs.length} document(s) indexed!`, 'success');
      await loadProducts();
    } catch (err) {
      showToast(`Failed to add product: ${err.message}`, 'error');
    } finally {
      submitBtn.disabled = false;
      loadingEl.classList.add('hidden');
    }
  });

  loadProducts();
});
