document.addEventListener('DOMContentLoaded', () => {
  const countrySel = document.getElementById('gf-country');
  const citySel = document.getElementById('gf-city');
  const weekSel = document.getElementById('gf-week');
  const sortSel = document.getElementById('gf-sort');

  const figures = Array.from(document.querySelectorAll('.gallery-card'));
  if (!figures.length) return;
  const sections = Array.from(document.querySelectorAll('.gallery-week'));
  const originalGrids = sections
    .map(section => section.querySelector('.gallery-grid'))
    .filter(Boolean);

  const mergedSection = document.createElement('section');
  mergedSection.className = 'gallery-week gallery-week--merged';
  mergedSection.style.display = 'none';

  const mergedGrid = document.createElement('div');
  mergedGrid.className = 'gallery-grid';
  mergedSection.appendChild(mergedGrid);

  if (sections.length) {
    sections[0].parentNode.insertBefore(mergedSection, sections[0]);
  }

  // annotate original index
  figures.forEach((fig, i) => {
    fig.setAttribute('data-original-index', i);
    fig._originalGrid = fig.parentElement;
    fig._originalSection = fig.closest('.gallery-week');
  });

  // collect unique values
  const countries = new Set();
  const cities = new Set();
  const weeks = new Set();
  figures.forEach(fig => {
    const img = fig.querySelector('img');
    const c = (img && img.dataset.country) ? img.dataset.country.trim() : '';
    const ci = (img && img.dataset.city) ? img.dataset.city.trim() : '';
    const w = (img && img.dataset.week) ? img.dataset.week.trim() : '';
    if (c) countries.add(c);
    if (ci) cities.add(ci);
    if (w) weeks.add(w);
  });

  function populate(sel, items) {
    // clear (keep first 'All' option)
    while (sel.children.length > 1) sel.removeChild(sel.lastChild);
    Array.from(items).sort((a,b)=>a.localeCompare(b,'nb')).forEach(it => {
      const opt = document.createElement('option'); opt.value = it; opt.textContent = it; sel.appendChild(opt);
    });
  }
  populate(countrySel, countries);
  populate(citySel, cities);
  populate(weekSel, weeks);

  function matchesFilters(fig) {
    const img = fig.querySelector('img');
    const c = (img && img.dataset.country) ? img.dataset.country.trim() : '';
    const ci = (img && img.dataset.city) ? img.dataset.city.trim() : '';
    const w = (img && img.dataset.week) ? img.dataset.week.trim() : '';
    if (countrySel.value && countrySel.value !== c) return false;
    if (citySel.value && citySel.value !== ci) return false;
    if (weekSel.value && weekSel.value !== w) return false;
    return true;
  }

  function compareFigures(a, b, key) {
    if (key === 'original') return a.dataset.originalIndex - b.dataset.originalIndex;

    const ai = a.querySelector('img');
    const bi = b.querySelector('img');
    let av = '';
    let bv = '';

    if (key === 'caption') {
      av = a.querySelector('figcaption')?.innerText || '';
      bv = b.querySelector('figcaption')?.innerText || '';
    } else if (key === 'city') {
      av = ai?.dataset.city || '';
      bv = bi?.dataset.city || '';
    } else if (key === 'country') {
      av = ai?.dataset.country || '';
      bv = bi?.dataset.country || '';
    } else if (key === 'week') {
      av = ai?.dataset.week || '';
      bv = bi?.dataset.week || '';
    }

    return av.localeCompare(bv, 'nb') || (a.dataset.originalIndex - b.dataset.originalIndex);
  }

  function restoreOriginalLayout() {
    originalGrids.forEach(grid => {
      figures
        .filter(fig => fig._originalGrid === grid)
        .sort((a, b) => a.dataset.originalIndex - b.dataset.originalIndex)
        .forEach(fig => grid.appendChild(fig));
    });
  }

  function updateSectionVisibility() {
    sections.forEach(section => {
      const hasVisibleCards = Array.from(section.querySelectorAll('.gallery-card'))
        .some(fig => fig.style.display !== 'none');
      section.style.display = hasVisibleCards ? '' : 'none';
    });
  }

  function applySortAndFilter() {
    const key = sortSel.value || 'original';
    const visible = figures.filter(matchesFilters).sort((a, b) => compareFigures(a, b, key));
    const hidden = figures
      .filter(fig => !matchesFilters(fig))
      .sort((a, b) => a.dataset.originalIndex - b.dataset.originalIndex);

    if (key === 'original') {
      restoreOriginalLayout();
      mergedSection.style.display = 'none';

      visible.forEach(fig => { fig.style.display = 'block'; });
      hidden.forEach(fig => { fig.style.display = 'none'; });
      updateSectionVisibility();
      return;
    }

    sections.forEach(section => { section.style.display = 'none'; });
    mergedSection.style.display = visible.length ? '' : 'none';

    visible.forEach(fig => {
      mergedGrid.appendChild(fig);
      fig.style.display = 'block';
    });
    hidden.forEach(fig => {
      mergedGrid.appendChild(fig);
      fig.style.display = 'none';
    });
  }

  countrySel.addEventListener('change', () => { populate(citySel, new Set(figures.filter(f=>{const i=f.querySelector('img'); return !countrySel.value || (i.dataset.country||'')===countrySel.value}).map(f=>f.querySelector('img')?.dataset.city).filter(Boolean))); applySortAndFilter(); });
  citySel.addEventListener('change', applySortAndFilter);
  weekSel.addEventListener('change', applySortAndFilter);
  sortSel.addEventListener('change', applySortAndFilter);

  // initial apply
  applySortAndFilter();
});
