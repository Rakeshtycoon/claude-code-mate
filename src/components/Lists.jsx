import { useState } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage.js'
import { uid } from '../lib/format.js'
import EditableList from './EditableList.jsx'

function BucketList() {
  const [items, setItems] = useLocalStorage('bd.bucket', [])
  const [text, setText] = useState('')
  const [year, setYear] = useState('')

  function add(e) {
    e.preventDefault()
    if (!text.trim()) return
    setItems([...items, { id: uid(), text: text.trim(), year: year.trim(), done: false }])
    setText('')
    setYear('')
  }
  function toggle(id) {
    setItems(items.map((i) => (i.id === id ? { ...i, done: !i.done } : i)))
  }
  function remove(id) {
    setItems(items.filter((i) => i.id !== id))
  }

  return (
    <section className="list-card">
      <h3 className="list-title">20 Things Before I Die</h3>
      <ol className="bucket">
        {items.map((it) => (
          <li key={it.id} className={it.done ? 'done' : ''}>
            <input type="checkbox" checked={!!it.done} onChange={() => toggle(it.id)} />
            <span className="checklist-text">{it.text}</span>
            {it.year && <span className="tag">{it.year}</span>}
            <button className="icon-btn" title="Remove" onClick={() => remove(it.id)}>
              ✕
            </button>
          </li>
        ))}
        {items.length === 0 && <li className="checklist-empty">Add your first wish.</li>}
      </ol>
      <form className="inline-add" onSubmit={add}>
        <input
          type="text"
          placeholder="My wish before I die…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <input
          type="text"
          className="year-input"
          placeholder="Year"
          value={year}
          onChange={(e) => setYear(e.target.value)}
        />
        <button className="btn small" type="submit">
          Add
        </button>
      </form>
    </section>
  )
}

export default function Lists() {
  const [rituals, setRituals] = useLocalStorage('bd.rituals', [])
  const [quotes, setQuotes] = useLocalStorage('bd.quotes', [])

  return (
    <div>
      <header className="page-head">
        <div>
          <h1>Lists</h1>
          <p className="muted">The habits, words and dreams that keep you going.</p>
        </div>
      </header>

      <div className="grid-2">
        <EditableList
          title="Daily Rituals — what you do for the business every day"
          items={rituals}
          onChange={setRituals}
          placeholder="Add a daily ritual…"
        />
        <EditableList
          title="My Empowering Lines & Quotes"
          items={quotes}
          onChange={setQuotes}
          checkable={false}
          placeholder="A line that gives you strength…"
        />
      </div>
      <BucketList />
    </div>
  )
}
