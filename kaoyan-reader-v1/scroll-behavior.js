export const PLAYER_SCROLL_HIDE_CSS = `
.player-shell.is-collapsed {
  transform: translate(-50%, calc(100% + 40px));
  opacity: 0;
  pointer-events: none;
}
`;

export function installPlayerScrollStyles(doc = globalThis.document) {
  if (!doc || doc.getElementById('player-scroll-hide-style')) return;
  const style = doc.createElement('style');
  style.id = 'player-scroll-hide-style';
  style.textContent = PLAYER_SCROLL_HIDE_CSS;
  doc.head.appendChild(style);
}

export function resolvePlayerScroll({
  anchorY,
  currentY,
  hidden,
  threshold = 24,
  revealThreshold = 8,
  topBoundary = 8,
}) {
  const y = Math.max(0, Number(currentY) || 0);
  const anchor = Math.max(0, Number(anchorY) || 0);

  if (y <= topBoundary) {
    return { hidden: false, anchorY: y };
  }

  const delta = y - anchor;

  if (delta >= threshold) {
    return { hidden: true, anchorY: y };
  }

  if (delta <= -(hidden ? revealThreshold : threshold)) {
    return { hidden: false, anchorY: y };
  }

  return { hidden: Boolean(hidden), anchorY: anchor };
}

if (typeof document !== 'undefined') installPlayerScrollStyles(document);
