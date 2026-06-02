import { useState } from 'react'
import { useSettings } from '../hooks/useSettings.js'
import { ACCENTS, DEFAULT_MANTRAS } from '../lib/settings.js'

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

export default function Settings() {
  const [settings, setSettings] = useSettings()
  const [newMantra, setNewMantra] = useState('')

  function patch(p) {
    setSettings({ ...settings, ...p })
  }

  function addMantra(e) {
    e.preventDefault()
    const text = newMantra.trim()
    if (!text) return
    patch({ mantras: [...settings.mantras, text] })
    setNewMantra('')
  }

  function editMantra(i, text) {
    const next = settings.mantras.slice()
    next[i] = text
    patch({ mantras: next })
  }

  function removeMantra(i) {
    patch({ mantras: settings.mantras.filter((_, idx) => idx !== i) })
  }

  function move(i, dir) {
    const j = i + dir
    if (j < 0 || j >= settings.mantras.length) return
    const next = settings.mantras.slice()
    ;[next[i], next[j]] = [next[j], next[i]]
    patch({ mantras: next })
  }

  return (
    <div>
      <header className="page-head">
        <div>
          <h1>Settings</h1>
          <p className="muted">Make the diary yours — mantras, financial year and colour.</p>
        </div>
      </header>

      {/* Accent colour */}
      <section className="card form">
        <h3 className="list-title">App colour</h3>
        <div className="swatches">
          {ACCENTS.map((a) => (
            <button
              key={a.key}
              type="button"
              className={`swatch ${settings.accent === a.key ? 'active' : ''}`}
              style={{ background: a.color }}
              title={a.label}
              onClick={() => patch({ accent: a.key })}
            />
          ))}
        </div>
        <p className="small-note">Changes the sidebar and headings colour.</p>
      </section>

      {/* Financial year */}
      <section className="card form">
        <h3 className="list-title">Financial year</h3>
        <label className="field">
          <span>Year starts in</span>
          <select
            value={settings.fyStartMonth}
            onChange={(e) => patch({ fyStartMonth: Number(e.target.value) })}
          >
            {MONTHS.map((m, i) => (
              <option key={m} value={i + 1}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <p className="small-note">
          The Yearly Plan and Graphs run for 12 months starting from this month.
        </p>
      </section>

      {/* Morning mantras */}
      <section className="card form">
        <div className="list-head-row">
          <h3 className="list-title">Morning Mantras</h3>
          <button
            className="btn small"
            type="button"
            onClick={() => patch({ mantras: DEFAULT_MANTRAS })}
          >
            Reset to default
          </button>
        </div>
        <ul className="mantra-edit-list">
          {settings.mantras.map((m, i) => (
            <li key={i}>
              <span className="reorder">
                <button className="icon-btn" title="Up" onClick={() => move(i, -1)}>↑</button>
                <button className="icon-btn" title="Down" onClick={() => move(i, 1)}>↓</button>
              </span>
              <input type="text" value={m} onChange={(e) => editMantra(i, e.target.value)} />
              <button className="icon-btn" title="Remove" onClick={() => removeMantra(i)}>✕</button>
            </li>
          ))}
          {settings.mantras.length === 0 && (
            <li className="checklist-empty">No mantras — add one below.</li>
          )}
        </ul>
        <form className="inline-add" onSubmit={addMantra}>
          <input
            type="text"
            value={newMantra}
            placeholder="Add a morning mantra…"
            onChange={(e) => setNewMantra(e.target.value)}
          />
          <button className="btn small" type="submit">Add</button>
        </form>
        <p className="small-note">These show as checkboxes on the Daily page each morning.</p>
      </section>
    </div>
  )
}
