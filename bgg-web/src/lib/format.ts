export function formatRange(min: number | null | undefined, max: number | null | undefined) {
  if (typeof min !== 'number' || typeof max !== 'number') return '—'
  if (min === max) return String(min)
  return `${min}–${max}`
}

export function formatNumber(value: unknown, digits = 2) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : '—'
}

export function clamp01(x: number) {
  if (x < 0) return 0
  if (x > 1) return 1
  return x
}