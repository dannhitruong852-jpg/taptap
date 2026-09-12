export const SPEED_STOPS = Object.freeze([0.7, 1, 1.3, 1.7]);
export function snapSpeed(value) {
  if (!Number.isFinite(Number(value))) return 1;
  return SPEED_STOPS.reduce((best, rate) => Math.abs(rate-value) < Math.abs(best-value) ? rate : best);
}
export function formatSpeed(rate) {
  const rounded = Number(Number(rate).toFixed(1));
  return `${rounded.toFixed(1)}×`;
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
  const trigger=root.querySelector('#speed-value,.speed-value');
  const menu=root.querySelector('.speed-menu');
  const options=[...root.querySelectorAll('[data-speed]')];
  let rate=1;
  function setOpen(open){
    root.classList.toggle('is-open',open);
    trigger.setAttribute('aria-expanded',String(open));
    menu.hidden=!open;
  }
  function select(next){
    rate=snapSpeed(Number(next));
    const label=formatSpeed(rate);
    trigger.textContent=label;
    trigger.setAttribute('aria-label',`倍速 ${label}`);
    options.forEach(option=>{
      const selected=Number(option.dataset.speed)===rate;
      option.classList.toggle('is-selected',selected);
      option.setAttribute('aria-checked',String(selected));
    });
    onRate(rate);
    setOpen(false);
  }
  trigger.addEventListener('click',event=>{event.stopPropagation();setOpen(!root.classList.contains('is-open'));});
  options.forEach(option=>option.addEventListener('click',event=>{event.stopPropagation();select(option.dataset.speed);}));
  document.addEventListener('click',event=>{if(!root.contains(event.target))setOpen(false);});
  root.addEventListener('keydown',event=>{
    if(event.key==='Escape'){setOpen(false);trigger.focus();}
  });
  setOpen(false);
  select(1);
  return {setRate:select,close:()=>setOpen(false),getRate:()=>rate};
}
