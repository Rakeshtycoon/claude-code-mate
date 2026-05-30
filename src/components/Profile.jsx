import { useRef, useState } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage.js'

const FIELDS = [
  { key: 'name', label: 'Name' },
  { key: 'company', label: 'Company Name' },
  { key: 'mobile', label: 'Mobile' },
  { key: 'email', label: 'E-mail' },
  { key: 'introducer', label: 'Introducer' },
  { key: 'membershipDate', label: 'Membership Date', type: 'date' },
  { key: 'membershipNo', label: 'Membership No.' },
  { key: 'pa', label: 'PA' },
]

const EMPTY = {
  name: '',
  company: '',
  mobile: '',
  email: '',
  introducer: '',
  membershipDate: '',
  membershipNo: '',
  pa: '',
  address: '',
  vision: '',
  mission: '',
  coreValues: '',
  photo: '',
}

// Shrink the chosen image to a small square so it fits comfortably in
// localStorage and loads instantly in the sidebar.
function resizePhoto(file, size = 256) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const img = new Image()
      img.onload = () => {
        const side = Math.min(img.width, img.height)
        const sx = (img.width - side) / 2
        const sy = (img.height - side) / 2
        const canvas = document.createElement('canvas')
        canvas.width = size
        canvas.height = size
        const ctx = canvas.getContext('2d')
        ctx.drawImage(img, sx, sy, side, side, 0, 0, size, size)
        resolve(canvas.toDataURL('image/jpeg', 0.85))
      }
      img.onerror = reject
      img.src = reader.result
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

export default function Profile() {
  const [profile, setProfile] = useLocalStorage('bd.profile', EMPTY)
  const [saved, setSaved] = useState(false)
  const fileRef = useRef(null)

  function set(key, value) {
    setProfile({ ...profile, [key]: value })
  }

  async function onPhoto(e) {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const dataUrl = await resizePhoto(file)
      set('photo', dataUrl)
    } catch {
      alert('Could not read that image. Try another photo.')
    }
    e.target.value = ''
  }

  // Data is already persisted on every keystroke; this button is a clear
  // "Save" affordance that confirms everything is stored.
  function save() {
    setProfile({ ...profile })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div>
      <header className="page-head">
        <div>
          <h1>Company &amp; Personal Details</h1>
          <p className="muted">Your identity, vision and values — the front page of the diary.</p>
        </div>
        <button className="btn primary" type="button" onClick={save}>
          {saved ? '✓ Saved' : 'Save'}
        </button>
      </header>

      <div className="card form">
        <div className="photo-row">
          <div className="photo-avatar">
            {profile.photo ? (
              <img src={profile.photo} alt="Profile" />
            ) : (
              <span>{(profile.name || 'PA').slice(0, 2).toUpperCase()}</span>
            )}
          </div>
          <div className="photo-actions">
            <span className="field-label">Profile Photo</span>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              className="hidden-file"
              onChange={onPhoto}
            />
            <div className="photo-buttons">
              <button
                className="btn small"
                type="button"
                onClick={() => fileRef.current?.click()}
              >
                {profile.photo ? 'Change photo' : 'Upload photo'}
              </button>
              {profile.photo && (
                <button className="btn small ghost" type="button" onClick={() => set('photo', '')}>
                  Remove
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="grid-2">
          {FIELDS.map((f) => (
            <label key={f.key} className="field">
              <span>{f.label}</span>
              <input
                type={f.type || 'text'}
                value={profile[f.key] || ''}
                onChange={(e) => set(f.key, e.target.value)}
              />
            </label>
          ))}
        </div>
        <label className="field">
          <span>Address</span>
          <textarea
            rows={2}
            value={profile.address || ''}
            onChange={(e) => set('address', e.target.value)}
          />
        </label>
      </div>

      <div className="card form">
        <label className="field">
          <span>Vision</span>
          <textarea
            rows={2}
            placeholder="Where are you going?"
            value={profile.vision || ''}
            onChange={(e) => set('vision', e.target.value)}
          />
        </label>
        <label className="field">
          <span>Mission</span>
          <textarea
            rows={2}
            placeholder="How will you get there?"
            value={profile.mission || ''}
            onChange={(e) => set('mission', e.target.value)}
          />
        </label>
        <label className="field">
          <span>Core Values</span>
          <textarea
            rows={2}
            placeholder="What you stand for"
            value={profile.coreValues || ''}
            onChange={(e) => set('coreValues', e.target.value)}
          />
        </label>
      </div>

      <div className="save-bar">
        <button className="btn primary" type="button" onClick={save}>
          {saved ? '✓ Saved' : 'Save details'}
        </button>
      </div>
    </div>
  )
}
