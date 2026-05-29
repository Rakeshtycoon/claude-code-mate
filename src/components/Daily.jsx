import { useLocalStorage } from '../hooks/useLocalStorage.js'
import { todayISO } from '../lib/format.js'
import { useState } from 'react'
import EditableList from './EditableList.jsx'

const MANTRAS = [
  'Prayer / Gratitude',
  'Yoga / Walk / Exercise',
  'Affirmation',
  'Learn / Read',
  'Sharing',
  'Sales Report PA App',
  'Task Sheet Post in Group',
  'Growth Action',
]

const LISTS = [
  { key: 'yearlyGoal', title: 'Action to Achieve My Yearly Goal' },
  { key: 'visits', title: 'Visit / One to One / Zoom Call' },
  { key: 'followups', title: 'Follow up & Reminder via Calls / Msg.' },
  { key: 'quotations', title: 'Quotation / Inquiry / Pending to Close' },
  { key: 'operations', title: 'Operation and Other Task' },
  { key: 'business', title: 'Business' },
  { key: 'teamFollow', title: 'Team Follow / Customer Follow' },
  { key: 'otherFollow', title: 'Other Follow' },
  { key: 'familyOther', title: 'Family / Other' },
]

function emptyDay() {
  return {
    mantras: {},
    month: { salesTarget: '', salesAchieved: '', collTarget: '', collAchieved: '' },
    today: { salesTarget: '', salesAchieved: '', collTarget: '', collAchieved: '' },
    lists: {},
  }
}

function shiftDate(iso, days) {
  const d = new Date(iso)
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

function TargetTable({ label, data, onChange }) {
  function set(field, value) {
    onChange({ ...data, [field]: value })
  }
  return (
    <div className="target-block">
      <div className="target-title">{label}</div>
      <table className="target-table">
        <thead>
          <tr>
            <th></th>
            <th>Target</th>
            <th>Achieved</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th>Sales</th>
            <td>
              <input
                type="number"
                value={data.salesTarget}
                onChange={(e) => set('salesTarget', e.target.value)}
              />
            </td>
            <td>
              <input
                type="number"
                value={data.salesAchieved}
                onChange={(e) => set('salesAchieved', e.target.value)}
              />
            </td>
          </tr>
          <tr>
            <th>Collection</th>
            <td>
              <input
                type="number"
                value={data.collTarget}
                onChange={(e) => set('collTarget', e.target.value)}
              />
            </td>
            <td>
              <input
                type="number"
                value={data.collAchieved}
                onChange={(e) => set('collAchieved', e.target.value)}
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

export default function Daily() {
  const [days, setDays] = useLocalStorage('bd.days', {})
  const [date, setDate] = useState(todayISO())

  const day = days[date] || emptyDay()

  function updateDay(next) {
    setDays({ ...days, [date]: next })
  }

  function toggleMantra(m) {
    updateDay({ ...day, mantras: { ...day.mantras, [m]: !day.mantras[m] } })
  }

  function setList(key, items) {
    updateDay({ ...day, lists: { ...day.lists, [key]: items } })
  }

  const weekday = new Date(date).toLocaleDateString(undefined, { weekday: 'long' })
  const dateLabel = new Date(date).toLocaleDateString(undefined, {
    month: 'long',
    day: 'numeric',
  })
  const mantrasDone = MANTRAS.filter((m) => day.mantras[m]).length

  return (
    <div>
      <header className="page-head daily-head">
        <div>
          <h1>{dateLabel}</h1>
          <p className="muted">{weekday}</p>
        </div>
        <div className="date-nav">
          <button className="btn" onClick={() => setDate(shiftDate(date, -1))}>
            ‹
          </button>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <button className="btn" onClick={() => setDate(shiftDate(date, 1))}>
            ›
          </button>
          <button className="btn" onClick={() => setDate(todayISO())}>
            Today
          </button>
        </div>
      </header>

      <div className="todo-feature">
        <EditableList
          title="📝 આજના કામ / To-Do"
          items={day.lists.todo || []}
          onChange={(items) => setList('todo', items)}
          placeholder="આજે શું કરવાનું છે? લખો…"
        />
      </div>

      <section className="card">
        <div className="section-bar">
          Morning Mantras{' '}
          <span className="muted">
            {mantrasDone}/{MANTRAS.length}
          </span>
        </div>
        <div className="mantras">
          {MANTRAS.map((m) => (
            <label key={m} className={`mantra ${day.mantras[m] ? 'on' : ''}`}>
              <input
                type="checkbox"
                checked={!!day.mantras[m]}
                onChange={() => toggleMantra(m)}
              />
              {m}
            </label>
          ))}
        </div>
      </section>

      <div className="grid-2">
        <div className="card">
          <TargetTable
            label="Month"
            data={day.month}
            onChange={(month) => updateDay({ ...day, month })}
          />
        </div>
        <div className="card">
          <TargetTable
            label="Today"
            data={day.today}
            onChange={(today) => updateDay({ ...day, today })}
          />
        </div>
      </div>

      <div className="grid-2">
        {LISTS.map((l) => (
          <EditableList
            key={l.key}
            title={l.title}
            items={day.lists[l.key] || []}
            onChange={(items) => setList(l.key, items)}
            placeholder="Add…"
          />
        ))}
      </div>
    </div>
  )
}
