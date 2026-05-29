import { useState } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage.js'
import EditableList from './EditableList.jsx'

function currentMonth() {
  return new Date().toISOString().slice(0, 7) // YYYY-MM
}

function monthLabel(ym) {
  const [y, m] = ym.split('-')
  return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString(undefined, {
    month: 'long',
    year: 'numeric',
  })
}

function pct(achieved, target) {
  const a = Number(achieved)
  const t = Number(target)
  if (!t) return null
  return Math.round((a / t) * 100)
}

function emptyPlan() {
  return {
    lastYear: { sales: '', profit: '', purchase: '', expense: '', other: '' },
    thisYear: { sales: '', profit: '', other: '' },
    comparison: '',
    target: { sales: '', profit: '', other: '' },
    achieved: '',
    noAction: [],
  }
}

function MoneyRow({ label, value, onChange }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type="number" value={value} onChange={(e) => onChange(e.target.value)} />
    </label>
  )
}

function PlanTab() {
  const [plans, setPlans] = useLocalStorage('bd.monthlyPlans', {})
  const [month, setMonth] = useState(currentMonth())
  const plan = plans[month] || emptyPlan()

  function update(next) {
    setPlans({ ...plans, [month]: next })
  }
  const setGroup = (group, field, value) =>
    update({ ...plan, [group]: { ...plan[group], [field]: value } })

  const achievedPct = pct(plan.achieved, plan.target.sales)

  return (
    <div>
      <div className="list-head">
        <h2>My Monthly Plan — {monthLabel(month)}</h2>
        <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} />
      </div>

      <div className="grid-2">
        <div className="card form">
          <h3 className="list-title">Last Year</h3>
          <MoneyRow label="Sales" value={plan.lastYear.sales} onChange={(v) => setGroup('lastYear', 'sales', v)} />
          <MoneyRow label="Profit" value={plan.lastYear.profit} onChange={(v) => setGroup('lastYear', 'profit', v)} />
          <MoneyRow label="Purchase" value={plan.lastYear.purchase} onChange={(v) => setGroup('lastYear', 'purchase', v)} />
          <MoneyRow label="Expense" value={plan.lastYear.expense} onChange={(v) => setGroup('lastYear', 'expense', v)} />
          <MoneyRow label="Other" value={plan.lastYear.other} onChange={(v) => setGroup('lastYear', 'other', v)} />
        </div>

        <div className="card form">
          <h3 className="list-title">This Year</h3>
          <MoneyRow label="Sales" value={plan.thisYear.sales} onChange={(v) => setGroup('thisYear', 'sales', v)} />
          <MoneyRow label="Profit" value={plan.thisYear.profit} onChange={(v) => setGroup('thisYear', 'profit', v)} />
          <MoneyRow label="Other" value={plan.thisYear.other} onChange={(v) => setGroup('thisYear', 'other', v)} />
          <label className="field">
            <span>Comparison</span>
            <div className="toggle">
              {['Growth', 'Same', 'De Growth'].map((c) => (
                <button
                  key={c}
                  type="button"
                  className={plan.comparison === c ? 'active' : ''}
                  onClick={() => update({ ...plan, comparison: c })}
                >
                  {c}
                </button>
              ))}
            </div>
          </label>
        </div>
      </div>

      <div className="grid-2">
        <div className="card form">
          <h3 className="list-title">Target</h3>
          <MoneyRow label="Sales" value={plan.target.sales} onChange={(v) => setGroup('target', 'sales', v)} />
          <MoneyRow label="Profit" value={plan.target.profit} onChange={(v) => setGroup('target', 'profit', v)} />
          <MoneyRow label="Other" value={plan.target.other} onChange={(v) => setGroup('target', 'other', v)} />
        </div>

        <div className="card form">
          <h3 className="list-title">Achieved</h3>
          <MoneyRow label="Achieved Sales" value={plan.achieved} onChange={(v) => update({ ...plan, achieved: v })} />
          <div className="achieved-pct">
            What percentage was achieved?
            <strong>{achievedPct === null ? ' —' : ` ${achievedPct}%`}</strong>
          </div>
        </div>
      </div>

      <EditableList
        title="I did not take any action to achieve the goal"
        items={plan.noAction || []}
        onChange={(items) => update({ ...plan, noAction: items })}
        placeholder="What got in the way?"
      />
    </div>
  )
}

function SalesTab() {
  const [rows, setRows] = useLocalStorage('bd.salesAnalysis', {})
  const [year, setYear] = useState(new Date().getFullYear())

  // April (year) → March (year+1), matching the diary's financial-year layout.
  const months = []
  for (let i = 0; i < 12; i++) {
    const m = (3 + i) % 12
    const y = 3 + i < 12 ? year : year + 1
    months.push({ key: `${y}-${String(m + 1).padStart(2, '0')}`, m, y })
  }

  function setCell(key, field, value) {
    const row = rows[key] || { lastYear: '', target: '', achieved: '', remark: '' }
    setRows({ ...rows, [key]: { ...row, [field]: value } })
  }

  return (
    <div>
      <div className="list-head">
        <h2>Sales Data Analysis — April {year} to March {year + 1}</h2>
        <input
          type="number"
          className="search"
          style={{ width: 110 }}
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
        />
      </div>
      <div className="card" style={{ overflowX: 'auto' }}>
        <table className="table sales-table">
          <thead>
            <tr>
              <th>Month</th>
              <th className="right">Last Year</th>
              <th className="right">Target</th>
              <th className="right">Achieved</th>
              <th className="right">%</th>
              <th>Remark</th>
            </tr>
          </thead>
          <tbody>
            {months.map(({ key, m, y }) => {
              const row = rows[key] || {}
              const p = pct(row.achieved, row.target)
              return (
                <tr key={key}>
                  <td>{new Date(y, m, 1).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}</td>
                  <td><input type="number" value={row.lastYear || ''} onChange={(e) => setCell(key, 'lastYear', e.target.value)} /></td>
                  <td><input type="number" value={row.target || ''} onChange={(e) => setCell(key, 'target', e.target.value)} /></td>
                  <td><input type="number" value={row.achieved || ''} onChange={(e) => setCell(key, 'achieved', e.target.value)} /></td>
                  <td className="right">{p === null ? '—' : `${p}%`}</td>
                  <td><input type="text" value={row.remark || ''} onChange={(e) => setCell(key, 'remark', e.target.value)} /></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function Monthly() {
  const [tab, setTab] = useState('plan')
  return (
    <div>
      <header className="page-head">
        <div>
          <h1>Monthly</h1>
          <p className="muted">Plan the month, then track sales across the year.</p>
        </div>
        <div className="toggle">
          <button className={tab === 'plan' ? 'active' : ''} onClick={() => setTab('plan')}>
            Monthly Plan
          </button>
          <button className={tab === 'sales' ? 'active' : ''} onClick={() => setTab('sales')}>
            Sales Analysis
          </button>
        </div>
      </header>
      {tab === 'plan' ? <PlanTab /> : <SalesTab />}
    </div>
  )
}
