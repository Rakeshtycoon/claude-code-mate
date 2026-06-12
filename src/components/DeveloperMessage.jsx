import { useState } from 'react'

// The developer's name and message. Replace MESSAGE (and add the photo at
// public/developer.jpg) with the real content.
const NAME = 'Rakesh Makani'
const MESSAGE = `Thank you for using Business Diary. I built this to help you stay
disciplined every single day — plan your work, track your sales and goals, and
keep your word to yourself. I hope it serves you well. — Rakesh`

export default function DeveloperMessage({ onClose }) {
  const [imgOk, setImgOk] = useState(true)
  const photo = `${import.meta.env.BASE_URL}developer.jpg`

  return (
    <div className="dev-overlay" onClick={onClose}>
      <div className="dev-modal" onClick={(e) => e.stopPropagation()}>
        <button className="dev-close" type="button" title="Close" onClick={onClose}>
          ✕
        </button>

        <div className="dev-photo">
          {imgOk ? (
            <img src={photo} alt={NAME} onError={() => setImgOk(false)} />
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
