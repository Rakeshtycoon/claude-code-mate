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
}

export default function Profile() {
  const [profile, setProfile] = useLocalStorage('bd.profile', EMPTY)

  function set(key, value) {
    setProfile({ ...profile, [key]: value })
  }

  return (
    <div>
      <header className="page-head">
        <div>
          <h1>Company &amp; Personal Details</h1>
          <p className="muted">Your identity, vision and values — the front page of the diary.</p>
        </div>
      </header>

      <div className="card form">
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
    </div>
  )
}
