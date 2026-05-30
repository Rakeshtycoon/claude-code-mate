/**
 * A small, dependency-free grouped bar chart rendered as responsive SVG.
 *
 * @param {object}   props
 * @param {Array}    props.data   [{ label, bars: [{ name, value, color }] }]
 * @param {number}   [props.height]
 * @param {Function} [props.format]  Formats values shown above bars.
 */
export default function BarChart({
  data = [],
  height = 200,
  format = (v) => v,
  scrollable = false,
}) {
  const hasData = data.some((g) => g.bars.some((b) => Number(b.value) > 0))

  if (!hasData) {
    return <p className="chart-empty">No data yet — fill it in and it’ll appear here.</p>
  }

  const groupW = 64
  const padX = 12
  const marginTop = 22
  const marginBottom = 30
  const width = Math.max(data.length * groupW + padX * 2, 260)
  const chartH = height - marginTop - marginBottom
  const baseY = marginTop + chartH

  let max = 0
  for (const g of data) for (const b of g.bars) max = Math.max(max, Number(b.value) || 0)
  if (max <= 0) max = 1

  const legend = data[0]?.bars || []

  return (
    <div className="chart">
      <div className="chart-legend">
        {legend.map((b) => (
          <span key={b.name} className="chart-legend-item">
            <span className="chart-swatch" style={{ background: b.color }} />
            {b.name}
          </span>
        ))}
      </div>
      <div className={scrollable ? 'chart-scroll' : ''}>
        <svg
          className="chart-svg"
          viewBox={`0 0 ${width} ${height}`}
          preserveAspectRatio="xMidYMid meet"
          style={scrollable ? { width: `${width}px`, maxWidth: 'none' } : undefined}
          role="img"
        >
        {/* baseline */}
        <line x1={padX} y1={baseY} x2={width - padX} y2={baseY} stroke="#e2e8f0" />
        {data.map((g, gi) => {
          const n = g.bars.length
          const gap = 5
          const innerW = groupW - 14
          const barW = (innerW - gap * (n - 1)) / n
          const gx = padX + gi * groupW + 7
          return (
            <g key={gi}>
              {g.bars.map((b, bi) => {
                const val = Number(b.value) || 0
                const h = Math.round((val / max) * chartH)
                const x = gx + bi * (barW + gap)
                const y = baseY - h
                return (
                  <g key={bi}>
                    <rect
                      x={x}
                      y={y}
                      width={barW}
                      height={h}
                      rx="2"
                      fill={b.color}
                    />
                    {val > 0 && (
                      <text
                        x={x + barW / 2}
                        y={y - 4}
                        textAnchor="middle"
                        className="chart-value"
                      >
                        {format(val)}
                      </text>
                    )}
                  </g>
                )
              })}
              <text
                x={gx + innerW / 2}
                y={baseY + 18}
                textAnchor="middle"
                className="chart-label"
              >
                {g.label}
              </text>
            </g>
          )
        })}
        </svg>
      </div>
    </div>
  )
}
