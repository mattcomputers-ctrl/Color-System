/**
 * Get CSS class for Delta E badge based on value.
 * Thresholds follow industry standards:
 *   < 1.0  = imperceptible (excellent)
 *   < 2.0  = perceptible but acceptable
 *   >= 2.0 = noticeable difference
 */
export function getDeltaEClass(deltaE) {
  if (deltaE === null || deltaE === undefined) return '';
  if (deltaE < 1.0) return 'delta-e-good';
  if (deltaE < 2.0) return 'delta-e-acceptable';
  return 'delta-e-poor';
}

export function getDeltaELabel(deltaE) {
  if (deltaE === null || deltaE === undefined) return 'N/A';
  if (deltaE < 1.0) return 'Excellent';
  if (deltaE < 2.0) return 'Acceptable';
  return 'Review';
}

/**
 * Convert LAB values to an approximate RGB hex color for display.
 * This is a rough approximation for UI preview purposes only.
 */
export function labToApproxHex(L, a, b) {
  if (L === null || L === undefined) return '#cccccc';

  // LAB to XYZ (D50)
  const fy = (L + 16) / 116;
  const fx = a / 500 + fy;
  const fz = fy - b / 200;
  const delta = 6.0 / 29.0;

  const xr = fx > delta ? fx * fx * fx : (fx - 16.0 / 116.0) * 3 * delta * delta;
  const yr = fy > delta ? fy * fy * fy : (fy - 16.0 / 116.0) * 3 * delta * delta;
  const zr = fz > delta ? fz * fz * fz : (fz - 16.0 / 116.0) * 3 * delta * delta;

  // D50 white point
  const X = xr * 0.9642;
  const Y = yr * 1.0;
  const Z = zr * 0.8251;

  // XYZ to sRGB (with D50 to D65 adaptation simplified)
  let r = X * 3.2406 + Y * -1.5372 + Z * -0.4986;
  let g = X * -0.9689 + Y * 1.8758 + Z * 0.0415;
  let bl = X * 0.0557 + Y * -0.2040 + Z * 1.0570;

  // Gamma correction
  const gamma = (c) => c > 0.0031308 ? 1.055 * Math.pow(c, 1 / 2.4) - 0.055 : 12.92 * c;
  r = Math.round(Math.max(0, Math.min(255, gamma(r) * 255)));
  g = Math.round(Math.max(0, Math.min(255, gamma(g) * 255)));
  bl = Math.round(Math.max(0, Math.min(255, gamma(bl) * 255)));

  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${bl.toString(16).padStart(2, '0')}`;
}

/**
 * Download a blob response as a file.
 */
export function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

/**
 * Format a date string for display.
 */
export function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}
