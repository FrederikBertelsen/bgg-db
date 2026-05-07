import { clamp01 } from '../lib/format'

type Props = {
  value: number | null | undefined
  outOf: number
  reverse?: boolean
  label: string
}

export function ScoreRing({ value, outOf, reverse, label }: Props) {
  const numeric = typeof value === 'number' && Number.isFinite(value) ? value : null
  const ratio = numeric === null ? null : clamp01(numeric / outOf)
  const radius = 16
  const circumference = 2 * Math.PI * radius
  const dash = ratio === null ? 0 : circumference * ratio
  const dashArray = `${dash} ${circumference - dash}`

  const scoreClass = 
    reverse ?
      ratio === null
        ? 'ring ring--na'
        : ratio > 0.6
          ? 'ring ring--low'
          : ratio >= 0.3
            ? 'ring ring--mid'
            : 'ring ring--high'
    : ratio === null
      ? 'ring ring--na'
      : ratio > 0.6
        ? 'ring ring--high'
        : ratio >= 0.3
          ? 'ring ring--mid'
          : 'ring ring--low'

  return (
    <div className="ringWrap" title={`${label}: ${numeric === null ? '—' : numeric.toFixed(2)}/${outOf}`}
    >
      <svg className={scoreClass} viewBox="0 0 40 40" aria-hidden="true">
        <circle className="ringTrack" cx="20" cy="20" r={radius} />
        <circle
          className="ringValue"
          cx="20"
          cy="20"
          r={radius}
          strokeDasharray={dashArray}
        />
      </svg>
      <div className="ringText">
        <div className="ringNumber">{numeric === null ? '—' : numeric.toFixed(1)}</div>
        <div className="ringLabel">{label}</div>
      </div>
    </div>
  )
}
