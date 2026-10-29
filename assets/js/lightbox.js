document.addEventListener('DOMContentLoaded', () => {
  const allImages = Array.from(document.querySelectorAll('.gallery-grid .gallery-card img'));
  if (!allImages.length) return;
  const countrySel = document.getElementById('gf-country');
  const citySel = document.getElementById('gf-city');
  const sortSel = document.getElementById('gf-sort');

  // create overlay
  const overlay = document.createElement('div');
  overlay.className = 'lb-overlay';
  overlay.innerHTML = `
    <button class="lb-close" aria-label="Lukk">×</button>
    <button class="lb-prev" aria-label="Forrige">‹</button>
    <div class="lb-frame">
      <img class="lb-image" src="" alt="" draggable="false">
      <div class="lb-caption"></div>
      <div class="lb-metadata"></div>
      <div class="lb-zoom-controls" aria-label="Zoomkontroller">
        <span class="lb-zoom-label">Zooming</span>
        <button class="lb-zoom-out" type="button" aria-label="Zoom ut">−</button>
        <span class="lb-zoom-level" aria-live="polite">100%</span>
        <button class="lb-zoom-in" type="button" aria-label="Zoom inn">+</button>
        <button class="lb-zoom-reset" type="button" aria-label="Tilbakestill zoom">Tilbakestill</button>
      </div>
    </div>
    <button class="lb-next" aria-label="Neste">›</button>
  `;
  document.body.appendChild(overlay);

  const lbImage = overlay.querySelector('.lb-image');
  const lbCaption = overlay.querySelector('.lb-caption');
  const btnClose = overlay.querySelector('.lb-close');
  const btnPrev = overlay.querySelector('.lb-prev');
  const btnNext = overlay.querySelector('.lb-next');
  const lbMetadata = overlay.querySelector('.lb-metadata');
  const btnZoomOut = overlay.querySelector('.lb-zoom-out');
  const btnZoomIn = overlay.querySelector('.lb-zoom-in');
  const btnZoomReset = overlay.querySelector('.lb-zoom-reset');
  const lbZoomLevel = overlay.querySelector('.lb-zoom-level');

  let currentIndex = 0;
  let zoom = 1;
  let panX = 0;
  let panY = 0;
  let pointerStart = null;
  const minZoom = 1;
  const maxZoom = 10;
  const zoomStep = 0.25;
  const wheelZoomStep = zoomStep / 3;

  function updateZoom() {
    const maxPanX = lbImage.offsetWidth * (zoom - minZoom) / 2;
    const maxPanY = lbImage.offsetHeight * (zoom - minZoom) / 2;
    panX = Math.min(maxPanX, Math.max(-maxPanX, panX));
    panY = Math.min(maxPanY, Math.max(-maxPanY, panY));
    lbImage.style.transform = `translate(${panX}px, ${panY}px) scale(${zoom})`;
    lbImage.classList.toggle('is-zoomed', zoom > minZoom);
    lbZoomLevel.textContent = `${Math.round(zoom * 100)}%`;
    btnZoomOut.disabled = zoom <= minZoom;
    btnZoomIn.disabled = zoom >= maxZoom;
  }

  function setZoom(nextZoom, centerX = 0, centerY = 0) {
    const newZoom = Math.min(maxZoom, Math.max(minZoom, nextZoom));
    if (newZoom === zoom) return;
    const ratio = newZoom / zoom;
    panX = (panX - centerX) * ratio + centerX;
    panY = (panY - centerY) * ratio + centerY;
    zoom = newZoom;
    if (zoom === minZoom) {
      panX = 0;
      panY = 0;
    }
    updateZoom();
  }

  function resetZoom() {
    zoom = minZoom;
    panX = 0;
    panY = 0;
    updateZoom();
  }

  function navigationImages() {
    const sortKey = sortSel?.value || 'original';
    const filteredImages = allImages.filter(img => {
      if (countrySel?.value && img.dataset.country !== countrySel.value) return false;
      if (citySel?.value && img.dataset.city !== citySel.value) return false;
      return true;
    });

    return filteredImages.sort((a, b) => {
      const aCard = a.closest('.gallery-card');
      const bCard = b.closest('.gallery-card');
      const aIndex = Number(aCard.dataset.originalIndex);
      const bIndex = Number(bCard.dataset.originalIndex);

      if (sortKey === 'original' || sortKey === 'original-reverse') {
        const weekOrder = Number(a.dataset.weekNumber) - Number(b.dataset.weekNumber);
        if (weekOrder) return weekOrder;
        return sortKey === 'original-reverse' ? bIndex - aIndex : aIndex - bIndex;
      }

      let aValue = '';
      let bValue = '';
      if (sortKey === 'caption') {
        aValue = aCard.querySelector('figcaption')?.innerText || '';
        bValue = bCard.querySelector('figcaption')?.innerText || '';
      } else if (sortKey === 'city') {
        aValue = a.dataset.city || '';
        bValue = b.dataset.city || '';
      } else if (sortKey === 'country') {
        aValue = a.dataset.country || '';
        bValue = b.dataset.country || '';
      } else if (sortKey === 'week') {
        aValue = a.dataset.week || '';
        bValue = b.dataset.week || '';
      }
      return aValue.localeCompare(bValue, 'nb') || aIndex - bIndex;
    });
  }

  function show(index) {
    const currentList = navigationImages();
    if (!currentList.length) return;
    index = ((index % currentList.length) + currentList.length) % currentList.length;
    currentIndex = index;
    const imgEl = currentList[index];
    document.dispatchEvent(new CustomEvent('gallery:select-week', { detail: { week: imgEl.dataset.week } }));
    const src = imgEl.getAttribute('data-large') || imgEl.dataset.src || imgEl.src;
    lbImage.src = src;
    lbImage.alt = imgEl.alt || '';
    const cap = imgEl.closest('figure')?.querySelector('figcaption')?.innerText || '';
    lbCaption.textContent = cap;
    // metadata from data attributes
    const city = imgEl.dataset.city || '';
    const country = imgEl.dataset.country || '';
    const week = imgEl.dataset.week || '';
    const metaParts = [];
    if (city) metaParts.push(city);
    if (country) metaParts.push(country);
    if (week) metaParts.push(week);
    lbMetadata.textContent = metaParts.join(' — ');

    overlay.classList.add('open');
    btnClose.focus();
  }

  function hide() {
    overlay.classList.remove('open');
    lbImage.src = '';
    lbMetadata.textContent = '';
    resetZoom();
  }

  allImages.forEach((img, i) => {
    img.setAttribute('data-lb-index', i);
    img.style.cursor = 'zoom-in';
    img.addEventListener('click', (e) => {
      e.preventDefault();
      const idx = navigationImages().indexOf(img);
      show(idx >= 0 ? idx : 0);
    });
  });

  btnClose.addEventListener('click', hide);
  btnPrev.addEventListener('click', () => show(currentIndex - 1));
  btnNext.addEventListener('click', () => show(currentIndex + 1));
  btnZoomIn.addEventListener('click', () => setZoom(zoom + zoomStep));
  btnZoomOut.addEventListener('click', () => setZoom(zoom - zoomStep));
  btnZoomReset.addEventListener('click', resetZoom);

  lbImage.addEventListener('wheel', event => {
    event.preventDefault();
    const bounds = lbImage.getBoundingClientRect();
    setZoom(zoom + (event.deltaY < 0 ? wheelZoomStep : -wheelZoomStep),
      event.clientX - (bounds.left + bounds.width / 2) + panX,
      event.clientY - (bounds.top + bounds.height / 2) + panY);
  }, { passive: false });
  lbImage.addEventListener('load', updateZoom);

  lbImage.addEventListener('pointerdown', event => {
    if (zoom <= minZoom || event.button !== 0) return;
    event.preventDefault();
    pointerStart = { x: event.clientX - panX, y: event.clientY - panY };
    lbImage.setPointerCapture(event.pointerId);
  });
  lbImage.addEventListener('pointermove', event => {
    if (!pointerStart) return;
    panX = event.clientX - pointerStart.x;
    panY = event.clientY - pointerStart.y;
    updateZoom();
  });
  lbImage.addEventListener('pointerup', () => { pointerStart = null; });
  lbImage.addEventListener('pointercancel', () => { pointerStart = null; });
  lbImage.addEventListener('dragstart', event => event.preventDefault());

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) hide();
  });

  document.addEventListener('keydown', (e) => {
    if (!overlay.classList.contains('open')) return;
    if (e.key === 'Escape') {
      e.preventDefault();
      hide();
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      show(currentIndex - 1);
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      show(currentIndex + 1);
    } else if (e.key === '+' || e.key === '=') {
      e.preventDefault();
      setZoom(zoom + zoomStep);
    } else if (e.key === '-') {
      e.preventDefault();
      setZoom(zoom - zoomStep);
    } else if (e.key === '0') {
      e.preventDefault();
      resetZoom();
    }
  });
});
