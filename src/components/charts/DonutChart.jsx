/**
 * A small dependency-free donut chart.
 *
 * @param {object} props
 * @param {Array}  props.data         [{ name, value, color }]
 * @param {number} [props.size]
 * @param {number} [props.thickness]
 * @param {string} [props.centerLabel]
 */
export default function DonutChart({ data = [], size = 160, thickness = 26, centerLabel = '' }) {
  const total = data.reduce((s, d) => s + (Number(d.value) || 0), 0)

  if (total <= 0) {
    return <p className="chart-empty">No data yet — add some and it’ll appear here.</p>
  }

  const r = (size - thickness) / 2
  const c = 2 * Math.PI * r
  const cx = size / 2
  const cy = size / 2
  let acc = 0

  return (
    <div className="donut">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="donut-svg"
        role="img"
      >
        <g transform={`rotate(-90 ${cx} ${cy})`}>
          {data.map((d, i) => {
            const val = Number(d.value) || 0
            if (val <= 0) return null
            const dash = (val / total) * c
            const el = (
              <circle
                key={i}
                cx={cx}
                cy={cy}
                r={r}
                fill="none"
                stroke={d.color}
                strokeWidth={thickness}
                strokeDasharray={`${dash} ${c - dash}`}
                strokeDashoffset={-acc}
              />
            )
            acc += dash
            return el
          })}
        </g>
        <text x={cx} y={cy - 2} textAnchor="middle" className="donut-total">
          {total}
        </text>
        <text x={cx} y={cy + 16} textAnchor="middle" className="donut-sub">
          {centerLabel}
        </text>
      </svg>
      <div className="donut-legend">
        {data.map((d, i) => (
          <span key={i} className="chart-legend-item">
            <span className="chart-swatch" style={{ background: d.color }} />
            {d.name} <strong>&nbsp;{d.value}</strong>
          </span>
        ))}
      </div>
    </div>
  )
}
