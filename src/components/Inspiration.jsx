import { useEffect, useState } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage.js'

/**
 * Gather all lines to rotate through: empowering quotes + bucket-list wishes.
 * Returns [{ text, kind, year }].
 */
export function useLines() {
  const [quotes] = useLocalStorage('bd.quotes', [])
  const [bucket] = useLocalStorage('bd.bucket', [])
  const lines = []
  for (const q of quotes) {
    if (q?.text?.trim()) lines.push({ text: q.text, kind: 'quote' })
  }
  for (const b of bucket) {
    if (b?.text?.trim()) lines.push({ text: b.text, kind: 'wish', year: b.year })
  }
  return lines
}

function kindLabel(line) {
  if (line.kind === 'wish') return line.year ? `🎯 Before I die · ${line.year}` : '🎯 Before I die'
  return '💬 Empowering line'
}

/** Compact auto-rotating banner for the Dashboard. */
export function QuoteRotator({ onOpen }) {
  const lines = useLines()
  const [i, setI] = useState(0)

  useEffect(() => {
    if (lines.length <= 1) return
    const id = setInterval(() => setI((n) => (n + 1) % lines.length), 6000)
    return () => clearInterval(id)
  }, [lines.length])

  // Keep index in range if the list shrinks.
  useEffect(() => {
    if (i >= lines.length) setI(0)
  }, [lines.length, i])

  if (lines.length === 0) {
    return (
      <div className="card rotator empty-rotator">
        <span className="vision-label">Inspiration</span>
        <p className="muted">
          Add lines in the <strong>Lists</strong> tab — they'll rotate here and
          in a full-screen slideshow.
        </p>
      </div>
    )
  }

  const line = lines[i] || lines[0]

  return (
    <div className="card rotator" onClick={onOpen} title="Tap for full-screen slideshow">
      <div className="rotator-top">
        <span className="vision-label">Inspiration</span>
        <button
          className="btn small"
          onClick={(e) => {
            e.stopPropagation()
            onOpen()
          }}
        >
          ▶ Full screen
        </button>
      </div>
      <p key={i} className="rotator-text fade-in">
        {line.text}
      </p>
      <span className="rotator-kind">{kindLabel(line)}</span>
    </div>
  )
}

/** Full-screen, auto-advancing slideshow overlay. */
export function Slideshow({ onClose }) {
  const lines = useLines()
  const [i, setI] = useState(0)
  const [playing, setPlaying] = useState(true)

  const next = () => setI((n) => (n + 1) % lines.length)
  const prev = () => setI((n) => (n - 1 + lines.length) % lines.length)

  useEffect(() => {
    if (!playing || lines.length <= 1) return
    const id = setInterval(next, 7000)
    return () => clearInterval(id)
  }, [playing, lines.length])

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') onClose()
      else if (e.key === 'ArrowRight') next()
      else if (e.key === 'ArrowLeft') prev()
      else if (e.key === ' ') {
        e.preventDefault()
        setPlaying((p) => !p)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [lines.length])

  const line = lines[i] || lines[0]

  return (
    <div className="slideshow">
      <div className="slideshow-bar">
        <span className="slideshow-count">
          {lines.length ? `${i + 1} / ${lines.length}` : '0'}
        </span>
        <button className="slideshow-close" onClick={onClose} title="Close (Esc)">
          ✕
        </button>
      </div>

      <div className="slideshow-stage" onClick={lines.length > 1 ? next : undefined}>
        {lines.length === 0 ? (
          <p className="slideshow-empty">
            No lines yet. Add some in the Lists tab.
          </p>
        ) : (
          <div key={i} className="slideshow-quote fade-in">
            <p className="slideshow-text">{line.text}</p>
            <span className="slideshow-kind">{kindLabel(line)}</span>
          </div>
        )}
      </div>

      {lines.length > 1 && (
        <div className="slideshow-controls">
          <button className="slideshow-btn" onClick={prev} title="Previous (←)">
            ‹
          </button>
          <button
            className="slideshow-btn"
            onClick={() => setPlaying((p) => !p)}
            title="Play / pause (space)"
          >
            {playing ? '❚❚' : '▶'}
          </button>
          <button className="slideshow-btn" onClick={next} title="Next (→)">
            ›
          </button>
        </div>
      )}
    </div>
  )
}
