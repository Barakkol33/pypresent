const slides = [...document.querySelectorAll('.slide')];
const rtl = document.documentElement.dir === 'rtl';
const bar = document.querySelector('.progress > i');
const counter = document.querySelector('.chrome .num');
const dots = document.querySelector('.chrome .dots');
let idx = 0;

slides.forEach((_, i) => dots.insertAdjacentHTML('beforeend', `<i data-i="${i}"></i>`));

// each column is measured on its own - otherwise the taller one drags the
// shorter one down with it and both end up smaller than they need to be
function fit(slide) {
  const body = slide.querySelector('.body');
  if (!body) return;
  const avail = body.clientHeight;
  slide.querySelectorAll('.fit').forEach(box => {
    box.style.transform = 'none';
    const need = Math.max(box.scrollHeight, box.getBoundingClientRect().height);
    box.style.transform = need > avail + 1 ? `scale(${Math.max(avail / need, 0.45)})` : 'none';
    box.dataset.scale = need > avail + 1 ? (avail / need).toFixed(3) : '1';
  });
}

// the slide is measured again after layout, fonts and the entry build settle
function refit() {
  fit(slides[idx]);
  requestAnimationFrame(() => fit(slides[idx]));
  [120, 400, 900].forEach(t => setTimeout(() => fit(slides[idx]), t));
}

function show(n) {
  idx = Math.max(0, Math.min(slides.length - 1, n));
  slides.forEach((s, i) => s.classList.toggle('active', i === idx));
  refit();
  bar.style.width = ((idx + 1) / slides.length * 100) + '%';
  counter.textContent = (idx + 1) + ' / ' + slides.length;
  [...dots.children].forEach((d, i) => d.classList.toggle('on', i === idx));
  if (location.hash !== '#' + (idx + 1)) history.replaceState(null, '', '#' + (idx + 1));
}

const next = () => show(idx + 1);
const prev = () => show(idx - 1);

addEventListener('keydown', e => {
  const fwd = rtl ? 'ArrowLeft' : 'ArrowRight';
  const back = rtl ? 'ArrowRight' : 'ArrowLeft';
  if (e.key === fwd || e.key === 'PageDown' || e.key === ' ' || e.key === 'ArrowDown') { next(); e.preventDefault(); }
  else if (e.key === back || e.key === 'PageUp' || e.key === 'ArrowUp') { prev(); e.preventDefault(); }
  else if (e.key === 'Home') show(0);
  else if (e.key === 'End') show(slides.length - 1);
  else if (e.key === 'f' || e.key === 'F') document.documentElement.requestFullscreen?.();
});
dots.addEventListener('click', e => { if (e.target.dataset.i) show(+e.target.dataset.i); });

let touch = null;
addEventListener('touchstart', e => touch = e.changedTouches[0].clientX, {passive: true});
addEventListener('touchend', e => {
  if (touch === null) return;
  const dx = e.changedTouches[0].clientX - touch;
  if (Math.abs(dx) > 50) (dx < 0) === !rtl ? next() : prev();
  touch = null;
}, {passive: true});

addEventListener('resize', () => fit(slides[idx]));
addEventListener('load', () => fit(slides[idx]));
document.fonts?.ready.then(() => fit(slides[idx]));
document.querySelectorAll('img').forEach(im => im.complete || (im.onload = () => fit(slides[idx])));
addEventListener('hashchange', () => show((parseInt(location.hash.slice(1)) || 1) - 1));
show((parseInt(location.hash.slice(1)) || 1) - 1);
