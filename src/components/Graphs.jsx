import { useLocalStorage } from '../hooks/useLocalStorage.js'
import { compactNumber } from '../lib/format.js'
import BarChart from './charts/BarChart.jsx'
import DonutChart from './charts/DonutChart.jsx'

const GOAL_CATS = [
  { key: 'business', label: 'Business' },
  { key: 'finance', label: 'Finance' },
  { key: 'family', label: 'Family' },
  { key: 'health', label: 'Health' },
  { key: 'pa', label: 'PA' },
  { key: 'crazy', label: 'Crazy' },
]

const GOAL_STATUS = [
  { key: 'toStart', name: 'To Start', color: '#9ca3af' },
  { key: 'ok', name: 'OK', color: '#16a34a' },
  { key: 'delay', name: 'Delay', color: '#d97706' },
  { key: 'stuck', name: 'Stuck', color: '#dc2626' },
  { key: 'cancel', name: 'Cancel', color: '#64748b' },
]

const num = (v) => Number(v) || 0

export default function Graphs({ onNavigate }) {
  const [goals] = useLocalStorage('bd.goals', {})
  const [days] = useLocalStorage('bd.days', {})
  const [plans] = useLocalStorage('bd.monthlyPlans', {})
  const [salesAnalysis] = useLocalStorage('bd.salesAnalysis', {})

  const month = new Date().toISOString().slice(0, 7)
  const plan = plans[month]

  // Goals progress per category + status counts.
  let totalGoals = 0
  const goalsByCat = GOAL_CATS.map((cat) => {
    const list = goals[cat.key] || []
    totalGoals += list.length
    return { label: cat.label, ok: list.filter((g) => g.status === 'ok').length, total: list.length }
  })
  const statusCounts = {}
  for (const cat of GOAL_CATS) {
    for (const g of goals[cat.key] || []) {
      statusCounts[g.status] = (statusCounts[g.status] || 0) + 1
    }
  }
  const donutData = GOAL_STATUS.map((s) => ({
    name: s.name,
    value: statusCounts[s.key] || 0,
    color: s.color,
  })).filter((d) => d.value > 0)

  // Monthly: This Year vs Last Year vs Target (sales & profit).
  const monthlyData = [
    {
      label: 'Sales',
      bars: [
        { name: 'Last Year', value: num(plan?.lastYear?.sales), color: '#94a3b8' },
        { name: 'This Year', value: num(plan?.thisYear?.sales), color: '#2563eb' },
        { name: 'Target', value: num(plan?.target?.sales), color: '#fbbf24' },
      ],
    },
    {
      label: 'Profit',
      bars: [
        { name: 'Last Year', value: num(plan?.lastYear?.profit), color: '#94a3b8' },
        { name: 'This Year', value: num(plan?.thisYear?.profit), color: '#2563eb' },
        { name: 'Target', value: num(plan?.target?.profit), color: '#fbbf24' },
      ],
    },
  ]

  // Sales Analysis: 12 months (financial year Apr→Mar).
  const fyYear = new Date().getFullYear()
  const salesYearData = []
  for (let i = 0; i < 12; i++) {
    const m = (3 + i) % 12
    const y = 3 + i < 12 ? fyYear : fyYear + 1
    const row = salesAnalysis[`${y}-${String(m + 1).padStart(2, '0')}`] || {}
    salesYearData.push({
      label: new Date(y, m, 1).toLocaleDateString(undefined, { month: 'short' }),
      bars: [
        { name: 'Target', value: num(row.target), color: '#93c5fd' },
        { name: 'Achieved', value: num(row.achieved), color: '#16a34a' },
      ],
    })
  }

  // Daily sales & collection: last 7 days Target vs Achieved.
  const sales7 = []
  const collection7 = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const dd = days[d.toISOString().slice(0, 10)]
    const label = String(d.getDate())
    sales7.push({
      label,
      bars: [
        { name: 'Target', value: num(dd?.today?.salesTarget), color: '#93c5fd' },
        { name: 'Achieved', value: num(dd?.today?.salesAchieved), color: '#ea580c' },
      ],
    })
    collection7.push({
      label,
      bars: [
        { name: 'Target', value: num(dd?.today?.collTarget), color: '#a7f3d0' },
        { name: 'Achieved', value: num(dd?.today?.collAchieved), color: '#0d9488' },
      ],
    })
  }

  return (
    <div>
      <header className="page-head">
        <div>
          <h1>Graphs</h1>
          <p className="muted">Comparisons from your Daily, Goals and Monthly data.</p>
        </div>
      </header>

      <section className="card">
        <div className="chart-head">
          <h3 className="list-title">
            📈 Monthly comparison — {new Date().toLocaleDateString(undefined, { month: 'long' })}
          </h3>
          <button className="btn small" onClick={() => onNavigate('monthly')}>Edit</button>
        </div>
        <BarChart data={monthlyData} format={compactNumber} />
      </section>

      <section className="card">
        <div className="chart-head">
          <h3 className="list-title">📊 Sales Analysis — 12 months (Target vs Achieved)</h3>
          <button className="btn small" onClick={() => onNavigate('monthly')}>Edit</button>
        </div>
        <BarChart data={salesYearData} format={compactNumber} scrollable />
      </section>

      <section className="card">
        <div className="chart-head">
          <h3 className="list-title">🎯 Goals progress by category</h3>
          <button className="btn small" onClick={() => onNavigate('goals')}>Edit</button>
        </div>
        {totalGoals === 0 ? (
          <p className="chart-empty">No goals yet — add some in the Goals tab.</p>
        ) : (
          <div className="goal-progress">
            {goalsByCat.map((c) => {
              const pct = c.total ? Math.round((c.ok / c.total) * 100) : 0
              return (
                <div key={c.label} className="gp-row">
                  <span className="gp-label">{c.label}</span>
                  <span className="gp-track">
                    <span className="gp-fill" style={{ width: `${pct}%` }} />
                  </span>
                  <span className="gp-count">{c.ok}/{c.total}</span>
                </div>
              )
            })}
          </div>
        )}
      </section>

      <section className="card">
        <div className="chart-head">
          <h3 className="list-title">🍩 Goals by status</h3>
          <button className="btn small" onClick={() => onNavigate('goals')}>Edit</button>
        </div>
        <DonutChart data={donutData} centerLabel="goals" />
      </section>

      <section className="card">
        <div className="chart-head">
          <h3 className="list-title">📅 Daily sales — Target vs Achieved (last 7 days)</h3>
          <button className="btn small" onClick={() => onNavigate('daily')}>Edit</button>
        </div>
        <BarChart data={sales7} format={compactNumber} />
      </section>

      <section className="card">
        <div className="chart-head">
          <h3 className="list-title">💵 Daily collection — Target vs Achieved (last 7 days)</h3>
          <button className="btn small" onClick={() => onNavigate('daily')}>Edit</button>
        </div>
        <BarChart data={collection7} format={compactNumber} />
      </section>
    </div>
  )
}
