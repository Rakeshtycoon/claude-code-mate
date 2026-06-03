/**
 * A tiny line+area trend chart (sparkline).
 *
 * @param {object} props
 * @param {Array}  props.points  [{ label, value }]
 * @param {string} [props.color]
 */
export default function Sparkline({ points = [], color = '#ea580c' }) {
  const w = 280
  const h = 70
  const pad = 8
  const labelH = 14
  const innerH = h - pad - labelH
  const max = Math.max(...points.map((p) => Number(p.value) || 0), 1)
  const n = points.length
  const step = n > 1 ? (w - pad * 2) / (n - 1) : 0

  const xy = points.map((p, i) => {
    const x = pad + i * step
    const y = pad + innerH - ((Number(p.value) || 0) / max) * innerH
    return [x, y]
  })

  const line = xy.map(([x, y]) => `${x},${y}`).join(' ')
  const area = `${pad},${pad + innerH} ${line} ${pad + (n - 1) * step},${pad + innerH}`

  return (
    <svg
      className="spark"
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="none"
      role="img"
    >
      <polygon points={area} fill={color} opacity="0.12" />
      <polyline points={line} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      {xy.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="2.5" fill={color} />
      ))}
      {points.map((p, i) => (
        <text key={i} x={pad + i * step} y={h - 2} textAnchor="middle" className="spark-label">
          {p.label}
        </text>
      ))}
    </svg>
  )
}
