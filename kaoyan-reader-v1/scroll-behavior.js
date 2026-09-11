export function resolvePlayerScroll({
  anchorY,
  currentY,
  hidden,
  threshold = 24,
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

  if (delta <= -threshold) {
    return { hidden: false, anchorY: y };
  }

  return { hidden: Boolean(hidden), anchorY: anchor };
}
