/**
 * Marketing page: single high-quality style transfer.
 * Form: upload image, select style, submit to POST /api/marketing/style-transfer.
 */
(function () {
  const form = document.getElementById('marketing-form');
  const photoInput = document.getElementById('photo-input');
  const uploadZone = document.getElementById('upload-zone');
  const uploadZoneInner = document.getElementById('upload-zone-inner');
  const uploadPreview = document.getElementById('upload-preview');
  const previewImg = document.getElementById('preview-img');
  const uploadRemove = document.getElementById('upload-remove');
  const styleSelect = document.getElementById('style-select');
  const submitBtn = document.getElementById('submit-btn');
  const errorEl = document.getElementById('error');
  const loadingEl = document.getElementById('loading');
  const resultEl = document.getElementById('result');
  const resultImg = document.getElementById('result-img');
  const downloadBtn = document.getElementById('download-btn');

  let selectedFile = null;

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.style.display = 'block';
    loadingEl.style.display = 'none';
  }

  function hideError() {
    errorEl.style.display = 'none';
  }

  function updateSubmitState() {
    submitBtn.disabled = !selectedFile || !styleSelect.value || styleSelect.value === '';
  }

  // Load styles
  fetch('/api/marketing/styles')
    .then(res => res.json())
    .then(styles => {
      styleSelect.innerHTML = '<option value="">Select a painting style</option>';
      const byPack = {};
      for (const s of styles) {
        const pack = s.pack_name || 'Other';
        if (!byPack[pack]) byPack[pack] = [];
        byPack[pack].push(s);
      }
      const packOrder = ['Masters', 'Impression & Color', 'Modern & Abstract', 'Ancient Worlds', 'Evolution of Portraits', 'Royalty & Power'];
      for (const pack of packOrder) {
        const items = byPack[pack];
        if (!items || items.length === 0) continue;
        const optgroup = document.createElement('optgroup');
        optgroup.label = pack;
        for (const s of items) {
          const opt = document.createElement('option');
          opt.value = `${s.style_id}-${s.style_index}`;
          opt.textContent = `${s.title || 'Style'} (${s.artist || 'Artist'})`;
          optgroup.appendChild(opt);
        }
        styleSelect.appendChild(optgroup);
      }
      updateSubmitState();
    })
    .catch(() => {
      styleSelect.innerHTML = '<option value="">Failed to load styles</option>';
      updateSubmitState();
    });

  // Upload zone
  uploadZone.addEventListener('click', () => photoInput.click());
  photoInput.addEventListener('change', (e) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  });

  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
  });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    const file = e.dataTransfer?.files?.[0];
    if (file && file.type.startsWith('image/')) handleFile(file);
  });

  uploadRemove.addEventListener('click', (e) => {
    e.stopPropagation();
    selectedFile = null;
    photoInput.value = '';
    uploadZoneInner.style.display = 'block';
    uploadPreview.style.display = 'none';
    updateSubmitState();
  });

  styleSelect.addEventListener('change', updateSubmitState);

  function handleFile(file) {
    if (file.size > 10 * 1024 * 1024) {
      showError('File must be under 10 MB');
      return;
    }
    selectedFile = file;
    hideError();
    const reader = new FileReader();
    reader.onload = () => {
      previewImg.src = reader.result;
      uploadZoneInner.style.display = 'none';
      uploadPreview.style.display = 'block';
    };
    reader.readAsDataURL(file);
    updateSubmitState();
  }

  // Submit
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!selectedFile || !styleSelect.value) return;

    const [styleId, styleIndex] = styleSelect.value.split('-').map(Number);
    const fd = new FormData();
    fd.append('image', selectedFile);
    fd.append('style_id', styleId);
    fd.append('style_index', styleIndex);

    hideError();
    resultEl.style.display = 'none';
    loadingEl.style.display = 'block';
    submitBtn.disabled = true;

    try {
      const res = await fetch('/api/marketing/style-transfer', {
        method: 'POST',
        body: fd,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      resultImg.src = url;
      downloadBtn.href = url;
      downloadBtn.download = `artify-result-${Date.now()}.jpg`;
      resultEl.style.display = 'block';
    } catch (err) {
      showError(err.message || 'Style transfer failed');
    } finally {
      loadingEl.style.display = 'none';
      submitBtn.disabled = false;
      updateSubmitState();
    }
  });
})();
