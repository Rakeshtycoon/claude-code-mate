import devPhoto from '../lib/devPhoto.js'

const NAME = 'Rakesh Makani'

// A short, honest note from the maker.
const MESSAGE = `I'm not a professional developer. I built Business Diary
myself — simply because I believed in one idea: a businessman's diary that
keeps you disciplined every single day.

If it helps even one person plan better, grow their work, and keep their word
to themselves, then every hour I spent on it was worth it.

Thank you for using it. — Rakesh`

export default function DeveloperMessage({ onClose }) {
  return (
    <div className="dev-overlay" onClick={onClose}>
      <div className="dev-modal" onClick={(e) => e.stopPropagation()}>
        <button className="dev-close" type="button" title="Close" onClick={onClose}>
          ✕
        </button>

        <div className="dev-photo">
          <img src={devPhoto} alt={NAME} />
        </div>

        <h3 className="dev-name">{NAME}</h3>
        <div className="dev-role">Developer</div>
        <p className="dev-msg">{MESSAGE}</p>
        <div className="dev-version">Business Diary · v1.0.1 ✓</div>
      </div>
    </div>
  )
}
