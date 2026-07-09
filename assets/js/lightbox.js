document.addEventListener('DOMContentLoaded', () => {
  const allImages = Array.from(document.querySelectorAll('.gallery-grid .gallery-card img'));
  if (!allImages.length) return;

  // create overlay
  const overlay = document.createElement('div');
  overlay.className = 'lb-overlay';
  overlay.innerHTML = `
    <button class="lb-close" aria-label="Lukk">×</button>
    <button class="lb-prev" aria-label="Forrige">‹<img class="lb-thumb lb-thumb-prev" src="" alt="Forrige bilde"/></button>
    <div class="lb-frame">
      <img class="lb-image" src="" alt="">
      <div class="lb-caption"></div>
      <div class="lb-metadata"></div>
    </div>
    <button class="lb-next" aria-label="Neste">›<img class="lb-thumb lb-thumb-next" src="" alt="Neste bilde"/></button>
  `;
  document.body.appendChild(overlay);

  const lbImage = overlay.querySelector('.lb-image');
  const lbCaption = overlay.querySelector('.lb-caption');
  const btnClose = overlay.querySelector('.lb-close');
  const btnPrev = overlay.querySelector('.lb-prev');
  const btnNext = overlay.querySelector('.lb-next');
  const lbThumbPrev = overlay.querySelector('.lb-thumb-prev');
  const lbThumbNext = overlay.querySelector('.lb-thumb-next');
  const lbMetadata = overlay.querySelector('.lb-metadata');

  let currentIndex = 0;
  let currentList = allImages;

  function show(index) {
    // ensure currentList reflects only visible images in DOM order
    currentList = Array.from(document.querySelectorAll('.gallery-grid .gallery-card img')).filter(i => {
      const fig = i.closest('.gallery-card');
      return fig && (fig.style.display !== 'none');
    });
    if (!currentList.length) return;
    index = ((index % currentList.length) + currentList.length) % currentList.length;
    currentIndex = index;
    const imgEl = currentList[index];
    const src = imgEl.getAttribute('data-large') || imgEl.src;
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

    // set prev/next thumbnails
    if (currentList.length > 1) {
      const prevIdx = ((index - 1) % currentList.length + currentList.length) % currentList.length;
      const nextIdx = (index + 1) % currentList.length;
      const prevEl = currentList[prevIdx];
      const nextEl = currentList[nextIdx];
      const prevSrc = prevEl.getAttribute('data-large') || prevEl.src;
      const nextSrc = nextEl.getAttribute('data-large') || nextEl.src;
      lbThumbPrev.src = prevSrc;
      lbThumbNext.src = nextSrc;
      lbThumbPrev.style.display = '';
      lbThumbNext.style.display = '';
    } else {
      lbThumbPrev.style.display = 'none';
      lbThumbNext.style.display = 'none';
      lbThumbPrev.src = '';
      lbThumbNext.src = '';
    }
    overlay.classList.add('open');
    btnClose.focus();
  }

  function hide() {
    overlay.classList.remove('open');
    lbImage.src = '';
    lbThumbPrev.src = '';
    lbThumbNext.src = '';
    lbMetadata.textContent = '';
  }

  allImages.forEach((img, i) => {
    img.setAttribute('data-lb-index', i);
    img.style.cursor = 'zoom-in';
    img.addEventListener('click', (e) => {
      e.preventDefault();
      // compute visible list and determine index within it
      const visible = Array.from(document.querySelectorAll('.gallery-grid .gallery-card img')).filter(i => i.closest('.gallery-card') && i.closest('.gallery-card').style.display !== 'none');
      const idx = visible.indexOf(img);
      show(idx >= 0 ? idx : 0);
    });
  });

  btnClose.addEventListener('click', hide);
  btnPrev.addEventListener('click', () => show(currentIndex - 1));
  btnNext.addEventListener('click', () => show(currentIndex + 1));

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) hide();
  });

  document.addEventListener('keydown', (e) => {
    if (!overlay.classList.contains('open')) return;
    if (e.key === 'Escape') hide();
    if (e.key === 'ArrowLeft') show(currentIndex - 1);
    if (e.key === 'ArrowRight') show(currentIndex + 1);
  });
});
