document.addEventListener('DOMContentLoaded', () => {
  const images = Array.from(document.querySelectorAll('.gallery-grid .gallery-card img'));
  if (!images.length) return;

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

  function show(index) {
    index = (index + images.length) % images.length;
    currentIndex = index;
    const src = images[index].getAttribute('data-large') || images[index].src;
    lbImage.src = src;
    lbImage.alt = images[index].alt || '';
    const cap = images[index].closest('figure')?.querySelector('figcaption')?.innerText || '';
    lbCaption.textContent = cap;
    overlay.classList.add('open');
    // focus for keyboard events
    btnClose.focus();
  }

  function hide() {
    overlay.classList.remove('open');
    lbImage.src = '';
  }

  images.forEach((img, i) => {
    img.setAttribute('data-lb-index', i);
    img.style.cursor = 'zoom-in';
    img.addEventListener('click', (e) => {
      e.preventDefault();
      show(i);
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
