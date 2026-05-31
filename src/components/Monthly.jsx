import { useState } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage.js'
import { formatMoney } from '../lib/format.js'
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

// Same month, one year earlier (e.g. "2026-05" -> "2025-05").
function lastYearMonth(ym) {
  const [y, m] = ym.split('-')
  return `${Number(y) - 1}-${m}`
}

function pct(achieved, target) {
  const a = Number(achieved)
  const t = Number(target)
  if (!t) return null
  return Math.round((a / t) * 100)
}

function emptyPlan() {
  return {
    comparison: '',
    target: { sales: '', collection: '', profit: '', other: '' },
    achieved: '',
    achievedCollection: '',
    noAction: [],
  }
}

// Target / Achieved metrics.
const PLAN_METRICS = [
  { field: 'sales', label: 'Sales' },
  { field: 'collection', label: 'Collection' },
  { field: 'profit', label: 'Profit' },
  { field: 'other', label: 'Other' },
]

// Last Year figures (the actuals recorded for that month a year ago).
const LAST_YEAR_METRICS = [
  { field: 'sales', label: 'Sales' },
  { field: 'collection', label: 'Collection' },
  { field: 'profit', label: 'Profit' },
  { field: 'purchase', label: 'Purchase' },
  { field: 'expense', label: 'Expense' },
  { field: 'other', label: 'Other' },
]

function MoneyRow({ label, value, onChange }) {
  return (
    <label className="field">
      <span>{label}</span>
      <span className="rupee">
        <input type="number" value={value} onChange={(e) => onChange(e.target.value)} />
      </span>
    </label>
  )
}

function PlanTab() {
  const [plans, setPlans] = useLocalStorage('bd.monthlyPlans', {})
  // Actual figures per month, keyed by absolute YYYY-MM and shared across years.
  const [actuals, setActuals] = useLocalStorage('bd.monthlyActuals', {})
  const [month, setMonth] = useState(currentMonth())
  const [editLastYear, setEditLastYear] = useState(false)
  const plan = plans[month] || emptyPlan()

  // "Last Year" is the same month one year ago — read from the shared store.
  const lastYearKey = lastYearMonth(month)
  const lastYearData = actuals[lastYearKey] || {}

  function update(next) {
    setPlans({ ...plans, [month]: next })
  }
  const setGroup = (group, field, value) =>
    update({ ...plan, [group]: { ...plan[group], [field]: value } })

  // Edits to Last Year write back to that month's actuals record.
  function setLastYearField(field, value) {
    setActuals({
      ...actuals,
      [lastYearKey]: { ...lastYearData, [field]: value },
    })
  }

  const achievedPct = pct(plan.achieved, plan.target.sales)
  const collectionPct = pct(plan.achievedCollection, plan.target.collection)

  return (
    <div>
      <div className="list-head">
        <h2>My Monthly Plan — {monthLabel(month)}</h2>
        <input
          type="month"
          value={month}
          onChange={(e) => {
            setMonth(e.target.value)
            setEditLastYear(false)
          }}
        />
      </div>

      <div className="grid-2">
        <div className="card form">
          <div className="list-head-row">
            <h3 className="list-title">Last Year — {monthLabel(lastYearKey)}</h3>
            <button className="btn small" type="button" onClick={() => setEditLastYear((v) => !v)}>
              {editLastYear ? '✓ Done' : 'Edit'}
            </button>
          </div>

          {editLastYear
            ? LAST_YEAR_METRICS.map(({ field, label }) => (
                <MoneyRow
                  key={field}
                  label={label}
                  value={lastYearData[field] || ''}
                  onChange={(v) => setLastYearField(field, v)}
                />
              ))
            : LAST_YEAR_METRICS.map(({ field, label }) => (
                <div key={field} className="readonly-row">
                  <span>{label}</span>
                  <strong>{lastYearData[field] ? formatMoney(lastYearData[field]) : '—'}</strong>
                </div>
              ))}

          <p className="small-note">
            {editLastYear
              ? `Saving to ${monthLabel(lastYearKey)} — these become last-year figures everywhere.`
              : `Auto-filled from ${monthLabel(lastYearKey)}. Tap Edit to adjust.`}
          </p>
        </div>

        <div className="card form">
          <h3 className="list-title">Target</h3>
          {PLAN_METRICS.map(({ field, label }) => (
            <MoneyRow
              key={field}
              label={label}
              value={plan.target[field] || ''}
              onChange={(v) => setGroup('target', field, v)}
            />
          ))}
          <label className="field" style={{ marginTop: 14 }}>
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

      <div className="card form">
        <h3 className="list-title">Achieved</h3>
        <div className="grid-2">
          <div>
            <MoneyRow label="Achieved Sales" value={plan.achieved} onChange={(v) => update({ ...plan, achieved: v })} />
            <div className="achieved-pct">
              Sales achieved
              <strong>{achievedPct === null ? ' —' : ` ${achievedPct}%`}</strong>
            </div>
          </div>
          <div>
            <MoneyRow label="Achieved Collection" value={plan.achievedCollection || ''} onChange={(v) => update({ ...plan, achievedCollection: v })} />
            <div className="achieved-pct">
              Collection achieved
              <strong>{collectionPct === null ? ' —' : ` ${collectionPct}%`}</strong>
            </div>
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
                  <td><span className="rupee"><input type="number" value={row.lastYear || ''} onChange={(e) => setCell(key, 'lastYear', e.target.value)} /></span></td>
                  <td><span className="rupee"><input type="number" value={row.target || ''} onChange={(e) => setCell(key, 'target', e.target.value)} /></span></td>
                  <td><span className="rupee"><input type="number" value={row.achieved || ''} onChange={(e) => setCell(key, 'achieved', e.target.value)} /></span></td>
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
