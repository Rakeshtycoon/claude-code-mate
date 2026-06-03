/**
 * A circular progress ring rendered as SVG.
 *
 * @param {object} props
 * @param {number} props.pct     0–100 (clamped). null/undefined shows an empty ring.
 * @param {string} props.color   Arc colour.
 * @param {number} [props.size]
 * @param {number} [props.stroke]
 */
export default function ProgressRing({ pct, color, size = 104, stroke = 11 }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const has = pct !== null && pct !== undefined
  const clamped = Math.max(0, Math.min(Number(pct) || 0, 100))
  const offset = c - (clamped / 100) * c
  const cx = size / 2

  return (
    <svg width={size} height={size} className="ring" role="img">
      <circle cx={cx} cy={cx} r={r} fill="none" stroke="var(--border)" strokeWidth={stroke} />
      {has && clamped > 0 && (
        <circle
          cx={cx}
          cy={cx}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={c}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cx})`}
        />
      )}
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central" className="ring-pct">
        {has ? `${clamped}%` : '—'}
      </text>
    </svg>
  )
}
