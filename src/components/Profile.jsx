import { useRef, useState } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage.js'
import PhotoCropper from './PhotoCropper.jsx'

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

export default function Profile() {
  const [profile, setProfile] = useLocalStorage('bd.profile', EMPTY)
  const [saved, setSaved] = useState(false)
  const [cropSrc, setCropSrc] = useState(null) // image awaiting crop/zoom
  const fileRef = useRef(null)

  function set(key, value) {
    setProfile({ ...profile, [key]: value })
  }

  // Read the chosen file and open the crop/zoom dialog.
  function onPhoto(e) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => setCropSrc(String(reader.result))
    reader.onerror = () => alert('Could not read that image. Try another photo.')
    reader.readAsDataURL(file)
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
      {cropSrc && (
        <PhotoCropper
          src={cropSrc}
          onCancel={() => setCropSrc(null)}
          onSave={(dataUrl) => {
            set('photo', dataUrl)
            setCropSrc(null)
          }}
        />
      )}

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
