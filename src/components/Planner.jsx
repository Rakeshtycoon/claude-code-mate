import { useState } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage.js'
import EditableList from './EditableList.jsx'

function currentMonth() {
  return new Date().toISOString().slice(0, 7)
}

function monthLabel(ym) {
  const [y, m] = ym.split('-')
  return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString(undefined, {
    month: 'long',
    year: 'numeric',
  })
}

// Build a Mon→Sun calendar grid for the given YYYY-MM.
function buildGrid(ym) {
  const [y, m] = ym.split('-').map(Number)
  const first = new Date(y, m - 1, 1)
  const daysInMonth = new Date(y, m, 0).getDate()
  // JS: 0=Sun … 6=Sat. Convert to Mon=0 … Sun=6.
  const lead = (first.getDay() + 6) % 7
  const cells = []
  for (let i = 0; i < lead; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)
  while (cells.length % 7 !== 0) cells.push(null)
  return cells
}

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const SIZES = [
  { label: 'Small', value: 11 },
  { label: 'Medium', value: 13 },
  { label: 'Large', value: 16 },
  { label: 'X-Large', value: 20 },
]

const COLORS = ['#0f172a', '#2563eb', '#16a34a', '#dc2626', '#ea580c', '#7c3aed']

export default function Planner() {
  const [month, setMonth] = useState(currentMonth())
  const [notes, setNotes] = useLocalStorage('bd.plannerNotes', {})
  const [nextPlans, setNextPlans] = useLocalStorage('bd.nextMonthPlans', {})
  const [noteStyle, setNoteStyle] = useLocalStorage('bd.plannerStyle', {
    fontSize: 12,
    color: '#0f172a',
  })

  const cellNoteStyle = { fontSize: `${noteStyle.fontSize}px`, color: noteStyle.color }

  const grid = buildGrid(month)
  const dayNotes = notes[month] || {}

  function setDayNote(day, text) {
    const next = { ...dayNotes, [day]: text }
    setNotes({ ...notes, [month]: next })
  }

  const today = new Date()
  const todayKey = today.toISOString().slice(0, 7)
  const todayDate = today.getDate()

  return (
    <div>
      <header className="page-head">
        <div>
          <h1>Monthly Planner</h1>
          <p className="muted">A bird's-eye view of {monthLabel(month)}.</p>
        </div>
        <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} />
      </header>

      <div className="card planner-toolbar">
        <span className="muted">Note style:</span>
        <label className="toolbar-field">
          <span>Size</span>
          <select
            value={noteStyle.fontSize}
            onChange={(e) => setNoteStyle({ ...noteStyle, fontSize: Number(e.target.value) })}
          >
            {SIZES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <span className="toolbar-field-label">Color</span>
        <div className="swatches">
          {COLORS.map((c) => (
            <button
              key={c}
              type="button"
              className={`swatch ${noteStyle.color === c ? 'active' : ''}`}
              style={{ background: c }}
              title={c}
              onClick={() => setNoteStyle({ ...noteStyle, color: c })}
            />
          ))}
          <input
            type="color"
            className="swatch-picker"
            value={noteStyle.color}
            title="Custom colour"
            onChange={(e) => setNoteStyle({ ...noteStyle, color: e.target.value })}
          />
        </div>
      </div>

      <div className="card">
        <div className="calendar">
          {WEEKDAYS.map((w) => (
            <div key={w} className="cal-weekday">
              {w}
            </div>
          ))}
          {grid.map((day, i) => (
            <div
              key={i}
              className={`cal-cell ${day ? '' : 'empty'} ${
                month === todayKey && day === todayDate ? 'today' : ''
              }`}
            >
              {day && (
                <>
                  <span className="cal-date">{day}</span>
                  <textarea
                    className="cal-note"
                    style={cellNoteStyle}
                    value={dayNotes[day] || ''}
                    placeholder="…"
                    onChange={(e) => setDayNote(day, e.target.value)}
                  />
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      <EditableList
        title={`My Planning for Next Month`}
        items={nextPlans[month] || []}
        onChange={(items) => setNextPlans({ ...nextPlans, [month]: items })}
        placeholder="What will you do next month?"
      />
    </div>
  )
}
