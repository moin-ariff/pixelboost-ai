const fileInput      = document.getElementById('fileInput');
const dropZone       = document.getElementById('dropZone');
const previewSection = document.getElementById('previewSection');
const previewOrig    = document.getElementById('previewOriginal');
const originalInfo   = document.getElementById('originalInfo');
const previewOut     = document.getElementById('previewOutput');
const outputInfo     = document.getElementById('outputInfo');
const outputTitle    = document.getElementById('outputTitle');
const spinner        = document.getElementById('spinner');
const outputStatus   = document.getElementById('outputStatus');
const actions        = document.getElementById('actions');
const upscaleBtn     = document.getElementById('upscaleBtn');
const downloadBtn    = document.getElementById('downloadBtn');
const statusBar      = document.getElementById('statusBar');
const btn2x          = document.getElementById('btn2x');
const btn4x          = document.getElementById('btn4x');
const btn8x          = document.getElementById('btn8x');
const btn16x         = document.getElementById('btn16x');

let selectedFile  = null;
let selectedScale = '4x';

// ── Scale Buttons ──────────────────────────────────────────
btn2x.addEventListener('click',  () => setScale('2x'));
btn4x.addEventListener('click',  () => setScale('4x'));
btn8x.addEventListener('click',  () => setScale('8x'));
btn16x.addEventListener('click', () => setScale('16x'));

function setScale(scale) {
  selectedScale = scale;
  btn2x.classList.toggle('active',  scale === '2x');
  btn4x.classList.toggle('active',  scale === '4x');
  btn8x.classList.toggle('active',  scale === '8x');
  btn16x.classList.toggle('active', scale === '16x');
  upscaleBtn.textContent = `Upscale Image ${scale}`;
}

// ── File Selection ─────────────────────────────────────────
fileInput.addEventListener('change', e => {
  if (e.target.files[0]) handleFile(e.target.files[0]);
});

dropZone.addEventListener('click', (e) => {
  if (e.target === dropZone || e.target.tagName === 'P' ||
      e.target.tagName === 'DIV') {
    fileInput.value = '';
    fileInput.click();
  }
});

dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
});

function handleFile(file) {
  selectedFile = file;
  const reader = new FileReader();
  reader.onload = e => {
    previewOrig.src = e.target.result;
    previewOrig.onload = () => {
      originalInfo.textContent =
        `${previewOrig.naturalWidth} x ${previewOrig.naturalHeight} pixels`;
    };
  };
  reader.readAsDataURL(file);

  previewOut.style.display   = 'none';
  outputStatus.style.display = 'block';
  outputStatus.textContent   = 'Click Upscale to process your image.';
  spinner.style.display      = 'none';
  downloadBtn.style.display  = 'none';
  outputInfo.textContent     = '';
  previewSection.style.display = 'flex';
  actions.style.display        = 'flex';
  setStatus('');
}

// ── Upscale Button ─────────────────────────────────────────
upscaleBtn.addEventListener('click', async () => {
  if (!selectedFile) {
    setStatus('Please select an image first!', 'error');
    return;
  }

  upscaleBtn.disabled    = true;
  upscaleBtn.textContent = 'Processing...';
  spinner.style.display      = 'block';
  outputStatus.style.display = 'none';
  previewOut.style.display   = 'none';
  downloadBtn.style.display  = 'none';
  outputTitle.textContent    = `Upscaled Image (${selectedScale})`;
  setStatus(`AI processing started — ${selectedScale} upscaling in progress...`, 'info');

  const formData = new FormData();
  formData.append('image', selectedFile);
  formData.append('scale', selectedScale);

  try {
    const res  = await fetch('/upscale', { method: 'POST', body: formData });
    const data = await res.json();

    if (!data.success) throw new Error(data.message);

    const outputUrl = data.image_url;
    previewOut.src  = outputUrl + '?t=' + Date.now();

    previewOut.onload = () => {
      spinner.style.display    = 'none';
      previewOut.style.display = 'block';
      outputInfo.textContent   =
        `${previewOut.naturalWidth} x ${previewOut.naturalHeight} pixels (${data.scale})`;

      // Fetch from Cloudinary and trigger direct download
      fetch(outputUrl)
        .then(res => res.blob())
        .then(blob => {
          const blobUrl            = window.URL.createObjectURL(blob);
          downloadBtn.href         = blobUrl;
          downloadBtn.target       = '';
          downloadBtn.download     = `upscaled_${data.scale}_${data.output_id}.jpg`;
          downloadBtn.style.display = 'inline-block';
        });

      setStatus(`Upscaling complete! Your ${data.scale} enhanced image is ready!`, 'success');
    };

  } catch (err) {
    spinner.style.display      = 'none';
    outputStatus.style.display = 'block';
    outputStatus.textContent   = 'An error occurred. Please try again.';
    setStatus('Error: ' + err.message, 'error');
  } finally {
    upscaleBtn.disabled    = false;
    upscaleBtn.textContent = `Upscale Image ${selectedScale}`;
  }
});

function setStatus(msg, type = '') {
  statusBar.textContent = msg;
  statusBar.className   = 'status-bar ' + type;
}