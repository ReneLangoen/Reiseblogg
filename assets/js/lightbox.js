document.addEventListener('DOMContentLoaded', () => {
  const allImages = Array.from(document.querySelectorAll('.gallery-grid .gallery-card img'));
  if (!allImages.length) return;

  // create overlay
  const overlay = document.createElement('div');
  overlay.className = 'lb-overlay';
  overlay.innerHTML = `
    <button class="lb-close" aria-label="Lukk">×</button>
    <button class="lb-prev" aria-label="Forrige">‹</button>
    <div class="lb-frame">
      <img class="lb-image" src="" alt="">
      <div class="lb-caption"></div>
    </div>
    <button class="lb-next" aria-label="Neste">›</button>
  `;
  document.body.appendChild(overlay);

  const lbImage = overlay.querySelector('.lb-image');
  const lbCaption = overlay.querySelector('.lb-caption');
  const btnClose = overlay.querySelector('.lb-close');
  const btnPrev = overlay.querySelector('.lb-prev');
  const btnNext = overlay.querySelector('.lb-next');

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
    overlay.classList.add('open');
    btnClose.focus();
  }

  function hide() {
    overlay.classList.remove('open');
    lbImage.src = '';
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
