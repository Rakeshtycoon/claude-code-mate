import { useState } from 'react'

const NAME = 'Rakesh Makani'

// A short, honest note from the maker.
const MESSAGE = `I'm not a professional developer. I built Business Diary
myself — simply because I believed in one idea: a businessman's diary that
keeps you disciplined every single day.

If it helps even one person plan better, grow their work, and keep their word
to themselves, then every hour I spent on it was worth it.

Thank you for using it. — Rakesh`

// Tries a transparent PNG first, then a JPG, then falls back to initials.
const base = import.meta.env.BASE_URL
const SOURCES = [`${base}developer.png`, `${base}developer.jpg`]

export default function DeveloperMessage({ onClose }) {
  const [idx, setIdx] = useState(0)
  const [failed, setFailed] = useState(false)

  function onImgError() {
    if (idx + 1 < SOURCES.length) setIdx(idx + 1)
    else setFailed(true)
  }

  return (
    <div className="dev-overlay" onClick={onClose}>
      <div className="dev-modal" onClick={(e) => e.stopPropagation()}>
        <button className="dev-close" type="button" title="Close" onClick={onClose}>
          ✕
        </button>

        <div className="dev-photo">
          {!failed ? (
            <img src={SOURCES[idx]} alt={NAME} onError={onImgError} />
          ) : (
            <span>{NAME.split(' ').map((w) => w[0]).join('').slice(0, 2)}</span>
          )}
        </div>

        <h3 className="dev-name">{NAME}</h3>
        <div className="dev-role">Developer</div>
        <p className="dev-msg">{MESSAGE}</p>
      </div>
    </div>
  )
}
