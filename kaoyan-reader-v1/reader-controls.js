// A continuous drag preview with five discrete, stable resting speeds.
export const SPEED_STOPS = Object.freeze([0.7, 1, 1.25, 1.5, 2]);
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
export function snapSpeed(value) {
  if (!Number.isFinite(Number(value))) return 1;
  return SPEED_STOPS.reduce((best, rate) => Math.abs(rate-value) < Math.abs(best-value) ? rate : best);
}
export function rateAtPosition(position) {
  const p = clamp(Number(position) || 0, 0, 4), i = Math.floor(p);
  return i === 4 ? 2 : SPEED_STOPS[i] + (SPEED_STOPS[i+1]-SPEED_STOPS[i])*(p-i);
}
export function formatSpeed(rate) {
  const rounded = Number(rate.toFixed(2));
  return `${Number.isInteger(rounded) ? rounded.toFixed(1) : rounded}\u00d7`;
}

// Never prevent pointer or context-menu defaults on the selectable article text.
export function createTapGuard({now = () => performance.now(), maxDuration = 450, maxMovement = 10} = {}) {
  let gesture = null;
  return {
    down(event, key, selected = false) {
      if (gesture && !gesture.ended && event.pointerId !== gesture.id) { gesture.blocked = true; return; }
      gesture = {id:event.pointerId, key, start:now(), x:event.clientX, y:event.clientY,
        blocked:selected || event.isPrimary === false || event.button > 0, ended:false};
    },
    move(event) {
      if (gesture && !gesture.ended && event.pointerId === gesture.id &&
          Math.hypot(event.clientX-gesture.x, event.clientY-gesture.y) > maxMovement) gesture.blocked = true;
    },
    up(event) {
      if (!gesture || event.pointerId !== gesture.id) return;
      this.move(event);
      gesture.blocked ||= now()-gesture.start >= maxDuration;
      gesture.ended = true;
    },
    cancel() { if (gesture) { gesture.blocked = true; gesture.ended = true; } },
    accept(key, selected, synthetic = false) {
      const g = gesture; gesture = null;
      return !selected && (g ? g.key === key && g.ended && !g.blocked : synthetic);
    },
    get active() { return Boolean(gesture && !gesture.ended); }
  };
}

export function attachSpeedControl(root, onRate) {
  const range = root.querySelector('input[type="range"]');
  const value = root.querySelector('.speed-value');
  const bubble = root.querySelector('.speed-bubble');
  let stablePosition = 1, numberDrag = null;
  function update(position) {
    const pos = clamp(Number(position) || 0, 0, 4);
    range.value = String(pos);
    const rate = Number(rateAtPosition(pos).toFixed(3));
    const label = formatSpeed(rate);
    value.textContent = label; bubble.textContent = label;
    range.setAttribute('aria-valuetext', label);
    root.style.setProperty('--speed-position', `${pos/4*100}%`);
    root.querySelectorAll('[data-stop]').forEach(el => el.classList.toggle('is-selected', Number(el.dataset.stop) === Math.round(pos)));
    onRate(rate);
  }
  function start() { root.classList.add('is-dragging'); }
  function finish(cancelled = false) {
    const position = cancelled ? stablePosition : Math.round(Number(range.value));
    stablePosition = position; update(position);
    root.classList.remove('is-dragging');
  }
  range.addEventListener('pointerdown', start);
  range.addEventListener('input', () => update(range.value));
  range.addEventListener('change', () => finish());
  range.addEventListener('pointerup', () => finish());
  range.addEventListener('pointercancel', () => finish(true));
  range.addEventListener('blur', () => finish());
  range.addEventListener('keydown', event => {
    const delta = {ArrowLeft:-1, ArrowDown:-1, ArrowRight:1, ArrowUp:1};
    let position = Math.round(Number(range.value));
    if (event.key in delta) position += delta[event.key];
    else if (event.key === 'Home') position = 0;
    else if (event.key === 'End') position = 4;
    else return;
    event.preventDefault(); stablePosition = clamp(position, 0, 4); update(stablePosition);
  });
  // The displayed number is itself a drag handle. Dragging is relative, so it
  // never jumps to 2x just because the finger started on the number at the right.
  value.addEventListener('pointerdown', event => {
    if (event.isPrimary === false || event.button > 0) return;
    event.preventDefault();
    numberDrag = {id:event.pointerId, x:event.clientX, position:Number(range.value)};
    value.setPointerCapture(event.pointerId); start();
  });
  value.addEventListener('pointermove', event => {
    if (!numberDrag || event.pointerId !== numberDrag.id) return;
    const width = Math.max(80, range.getBoundingClientRect().width);
    update(numberDrag.position + (event.clientX-numberDrag.x)/width*4);
  });
  const stopNumberDrag = cancelled => {
    if (!numberDrag) return;
    numberDrag = null; finish(cancelled);
  };
  value.addEventListener('pointerup', () => stopNumberDrag(false));
  value.addEventListener('pointercancel', () => stopNumberDrag(true));
  value.addEventListener('lostpointercapture', () => stopNumberDrag(false));
  value.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); range.focus(); }
  });
  update(stablePosition);
}
