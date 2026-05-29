import { useState } from 'react'
import { uid } from '../lib/format.js'

/**
 * A reusable add/check/delete list of text items.
 * Items have the shape { id, text, done }.
 *
 * @param {object}   props
 * @param {string}   props.title        Section heading.
 * @param {Array}    props.items        Current items.
 * @param {Function} props.onChange     Receives the next items array.
 * @param {string}   [props.placeholder]
 * @param {boolean}  [props.checkable]  Show a done checkbox per item (default true).
 */
export default function EditableList({
  title,
  items = [],
  onChange,
  placeholder = 'Add an item…',
  checkable = true,
}) {
  const [text, setText] = useState('')

  function add(e) {
    e.preventDefault()
    const value = text.trim()
    if (!value) return
    onChange([...items, { id: uid(), text: value, done: false }])
    setText('')
  }

  function toggle(id) {
    onChange(items.map((it) => (it.id === id ? { ...it, done: !it.done } : it)))
  }

  function remove(id) {
    onChange(items.filter((it) => it.id !== id))
  }

  return (
    <section className="list-card">
      {title && <h3 className="list-title">{title}</h3>}
      <ul className="checklist">
        {items.map((it) => (
          <li key={it.id} className={it.done ? 'done' : ''}>
            {checkable && (
              <input
                type="checkbox"
                checked={!!it.done}
                onChange={() => toggle(it.id)}
              />
            )}
            <span className="checklist-text">{it.text}</span>
            <button className="icon-btn" title="Remove" onClick={() => remove(it.id)}>
              ✕
            </button>
          </li>
        ))}
        {items.length === 0 && <li className="checklist-empty">Nothing yet.</li>}
      </ul>
      <form className="inline-add" onSubmit={add}>
        <input
          type="text"
          value={text}
          placeholder={placeholder}
          onChange={(e) => setText(e.target.value)}
        />
        <button className="btn small" type="submit">
          Add
        </button>
      </form>
    </section>
  )
}
