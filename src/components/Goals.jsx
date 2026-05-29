import { useState } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage.js'
import { uid } from '../lib/format.js'

const CATEGORIES = [
  { key: 'business', label: 'Business Goals' },
  { key: 'finance', label: 'Finance Goals' },
  { key: 'family', label: 'Family Goals' },
  { key: 'health', label: 'Health Goals' },
  { key: 'pa', label: 'Progress Alliance Goals' },
  { key: 'crazy', label: 'Crazy Goals' },
]

// Status cycle matches the diary legend.
const STATUSES = [
  { key: 'toStart', label: 'To Start', icon: '○', color: '#9ca3af' },
  { key: 'ok', label: 'OK', icon: '✓', color: '#16a34a' },
  { key: 'delay', label: 'Delay', icon: '»', color: '#d97706' },
  { key: 'stuck', label: 'Stuck', icon: '!', color: '#dc2626' },
  { key: 'cancel', label: 'Cancel', icon: '✕', color: '#6b7280' },
]

function statusFor(key) {
  return STATUSES.find((s) => s.key === key) || STATUSES[0]
}

const EMPTY = { business: [], finance: [], family: [], health: [], pa: [], crazy: [] }

export default function Goals() {
  const [goals, setGoals] = useLocalStorage('bd.goals', EMPTY)
  const [drafts, setDrafts] = useState({})

  function addGoal(cat, e) {
    e.preventDefault()
    const text = (drafts[cat] || '').trim()
    if (!text) return
    setGoals({
      ...goals,
      [cat]: [...(goals[cat] || []), { id: uid(), text, status: 'toStart' }],
    })
    setDrafts({ ...drafts, [cat]: '' })
  }

  function cycleStatus(cat, id) {
    setGoals({
      ...goals,
      [cat]: goals[cat].map((g) => {
        if (g.id !== id) return g
        const idx = STATUSES.findIndex((s) => s.key === g.status)
        return { ...g, status: STATUSES[(idx + 1) % STATUSES.length].key }
      }),
    })
  }

  function remove(cat, id) {
    setGoals({ ...goals, [cat]: goals[cat].filter((g) => g.id !== id) })
  }

  const year = new Date().getFullYear()

  return (
    <div>
      <header className="page-head">
        <div>
          <h1>My Goals in {year}</h1>
          <p className="muted">Tap a status chip to cycle it. “I am my word.”</p>
        </div>
      </header>

      <div className="legend">
        {STATUSES.map((s) => (
          <span key={s.key} className="legend-item">
            <span className="status-dot" style={{ color: s.color }}>
              {s.icon}
            </span>
            {s.label}
          </span>
        ))}
      </div>

      <div className="grid-2">
        {CATEGORIES.map((cat) => (
          <section key={cat.key} className="card goal-card">
            <h3 className="goal-head">{cat.label}</h3>
            <ul className="goal-list">
              {(goals[cat.key] || []).map((g) => {
                const st = statusFor(g.status)
                return (
                  <li key={g.id}>
                    <button
                      className="status-chip"
                      style={{ color: st.color, borderColor: st.color }}
                      title={st.label}
                      onClick={() => cycleStatus(cat.key, g.id)}
                    >
                      {st.icon}
                    </button>
                    <span className="goal-text">{g.text}</span>
                    <button
                      className="icon-btn"
                      title="Remove"
                      onClick={() => remove(cat.key, g.id)}
                    >
                      ✕
                    </button>
                  </li>
                )
              })}
              {(goals[cat.key] || []).length === 0 && (
                <li className="checklist-empty">No goals set.</li>
              )}
            </ul>
            <form className="inline-add" onSubmit={(e) => addGoal(cat.key, e)}>
              <input
                type="text"
                placeholder={`Add a ${cat.label.toLowerCase().replace(' goals', '')} goal…`}
                value={drafts[cat.key] || ''}
                onChange={(e) => setDrafts({ ...drafts, [cat.key]: e.target.value })}
              />
              <button className="btn small" type="submit">
                Add
              </button>
            </form>
          </section>
        ))}
      </div>
    </div>
  )
}
