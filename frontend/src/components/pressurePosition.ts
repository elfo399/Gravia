/** Board coordinates: positive x is right; positive y is front (up in SVG). */
export function pressurePosition(
  point: { x: number; y: number },
  origin: { x: number; y: number },
  scale: { x: number; y: number },
) {
  return {
    x: origin.x + Math.max(-1, Math.min(1, point.x)) * scale.x,
    y: origin.y - Math.max(-1, Math.min(1, point.y)) * scale.y,
  };
}
