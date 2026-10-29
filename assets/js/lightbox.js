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
      <img class="lb-image" src="" alt="">
      <div class="lb-caption"></div>
      <div class="lb-metadata"></div>
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

  let currentIndex = 0;

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
    }
  });
});
