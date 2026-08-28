// Injected into a built deck by `pypresent audit`, and never shipped with one.
// It activates every slide in turn, lets the deck's own fit() measure it, and
// reports the result in the page title, which --dump-dom can read back out.
addEventListener('load', () => {
  const rows = [...document.querySelectorAll('.slide')].map((s, i) => {
    s.classList.add('active');
    if (typeof fit === 'function') fit(s);
    const boxes = [...s.querySelectorAll('.fit')];
    const scales = boxes.map(b => Number(b.dataset.scale || 1));
    const body = s.querySelector('.body');
    const need = Math.max(0, ...boxes.map(b => b.scrollHeight));
    const fill = body && body.clientHeight ? need / body.clientHeight : 1;
    const title = (s.querySelector('.title')?.textContent || '').slice(0, 46);
    s.classList.remove('active');
    return [i + 1, Math.min(1, ...(scales.length ? scales : [1])), fill.toFixed(3), title].join('\t');
  });
  document.title = 'AUDIT\n' + rows.join('\n');
});
