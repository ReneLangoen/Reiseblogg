document.addEventListener('DOMContentLoaded', () => {
  const countrySel = document.getElementById('gf-country');
  const citySel = document.getElementById('gf-city');
  const weekSel = document.getElementById('gf-week');
  const sortSel = document.getElementById('gf-sort');

  const figures = Array.from(document.querySelectorAll('.gallery-card'));
  if (!figures.length) return;

  // annotate original index
  figures.forEach((fig, i) => fig.setAttribute('data-original-index', i));

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

  function applySortAndFilter() {
    // For each gallery-grid container, reorder its child figures
    const grids = document.querySelectorAll('.gallery-grid');
    grids.forEach(grid => {
      const figs = Array.from(grid.querySelectorAll('.gallery-card'));
      // filter
      const visible = figs.filter(f => matchesFilters(f));
      const hidden = figs.filter(f => !matchesFilters(f));

      // sort visible according to sortSel
      const key = sortSel.value || 'original';
      visible.sort((a,b) => {
        if (key === 'original') return (a.dataset.originalIndex - b.dataset.originalIndex);
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
        return av.localeCompare(bv, 'nb');
      });

      // reattach: first visible in sorted order, then hidden in original order
      visible.forEach(f => grid.appendChild(f));
      hidden.forEach(f => grid.appendChild(f));

      // set display: show visible, hide hidden
      visible.forEach(f => f.style.display = 'block');
      hidden.forEach(f => f.style.display = 'none');
    });
  }

  countrySel.addEventListener('change', () => { populate(citySel, new Set(figures.filter(f=>{const i=f.querySelector('img'); return !countrySel.value || (i.dataset.country||'')===countrySel.value}).map(f=>f.querySelector('img')?.dataset.city).filter(Boolean))); applySortAndFilter(); });
  citySel.addEventListener('change', applySortAndFilter);
  weekSel.addEventListener('change', applySortAndFilter);
  sortSel.addEventListener('change', applySortAndFilter);

  // initial apply
  applySortAndFilter();
});
