import { useRef, useState } from 'react'
import {
  downloadBackup,
  parseBackup,
  restoreBackup,
  summarize,
  collectData,
} from '../lib/backup.js'
import { formatDate } from '../lib/format.js'

export default function Backup() {
  const fileRef = useRef(null)
  const [message, setMessage] = useState(null) // { type, text }
  const [pending, setPending] = useState(null) // parsed backup awaiting confirm

  const liveSummary = summarize(collectData())

  function handleExport() {
    try {
      const backup = downloadBackup()
      const s = summarize(backup.data)
      setMessage({
        type: 'ok',
        text: `Backup downloaded — ${s.days} day(s), ${s.goals} goal(s). Save this file to your phone or upload it to Google Drive.`,
      })
    } catch {
      setMessage({ type: 'err', text: 'Could not create the backup file.' })
    }
  }

  function handleFile(e) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const parsed = parseBackup(String(reader.result))
        setPending(parsed)
        setMessage(null)
      } catch (err) {
        setPending(null)
        setMessage({ type: 'err', text: err.message })
      }
    }
    reader.onerror = () =>
      setMessage({ type: 'err', text: 'Could not read that file.' })
    reader.readAsText(file)
    // Allow re-selecting the same file later.
    e.target.value = ''
  }

  function confirmRestore() {
    try {
      restoreBackup(pending, { merge: false })
      // useLocalStorage reads on mount, so reload to show restored data.
      window.location.reload()
    } catch {
      setMessage({ type: 'err', text: 'Restore failed. Your data was not changed.' })
      setPending(null)
    }
  }

  const pendingSummary = pending ? summarize(pending.data) : null

  return (
    <div>
      <header className="page-head">
        <div>
          <h1>Backup &amp; Restore</h1>
          <p className="muted">
            Save your diary to a file, then load it on any phone or computer.
          </p>
        </div>
      </header>

      {message && (
        <div className={`banner ${message.type === 'err' ? 'banner-err' : 'banner-ok'}`}>
          {message.text}
        </div>
      )}

      <div className="grid-2">
        <section className="card backup-card">
          <h3 className="list-title">⬇️ Backup (save)</h3>
          <p className="muted backup-desc">
            Downloads one <code>.json</code> file with everything in your diary.
            Keep it in your phone storage or upload it to Google&nbsp;Drive.
          </p>
          <ul className="backup-stats">
            <li><strong>{liveSummary.days}</strong> daily page(s)</li>
            <li><strong>{liveSummary.goals}</strong> goal(s)</li>
            <li><strong>{liveSummary.monthlyPlans}</strong> monthly plan(s)</li>
            <li><strong>{liveSummary.rituals + liveSummary.quotes + liveSummary.bucket}</strong> list item(s)</li>
          </ul>
          <button className="btn primary" onClick={handleExport}>
            Download backup file
          </button>
        </section>

        <section className="card backup-card">
          <h3 className="list-title">⬆️ Restore (load)</h3>
          <p className="muted backup-desc">
            Pick a backup file from this device — including one you downloaded
            from Google&nbsp;Drive. Your old diary will come back.
          </p>
          <input
            ref={fileRef}
            type="file"
            accept="application/json,.json"
            className="hidden-file"
            onChange={handleFile}
          />
          <button className="btn" onClick={() => fileRef.current?.click()}>
            Choose backup file…
          </button>

          {pending && pendingSummary && (
            <div className="restore-confirm">
              <p>
                This backup is from{' '}
                <strong>{formatDate(pending.exportedAt?.slice(0, 10))}</strong> and
                contains <strong>{pendingSummary.days}</strong> day(s),{' '}
                <strong>{pendingSummary.goals}</strong> goal(s).
              </p>
              <p className="warn">
                ⚠️ Restoring will <strong>replace</strong> the data currently on
                this device. This cannot be undone — back up first if unsure.
              </p>
              <div className="link-row">
                <button className="btn primary" onClick={confirmRestore}>
                  Replace &amp; restore
                </button>
                <button className="btn" onClick={() => setPending(null)}>
                  Cancel
                </button>
              </div>
            </div>
          )}
        </section>
      </div>

      <section className="card">
        <h3 className="list-title">📂 Using Google Drive</h3>
        <ol className="how-to">
          <li>Tap <strong>Download backup file</strong> above.</li>
          <li>Open the Google&nbsp;Drive app and upload that file (or save it there).</li>
          <li>On your new phone, open Drive and download the file.</li>
          <li>Come here, tap <strong>Choose backup file…</strong>, pick it, and confirm.</li>
        </ol>
        <p className="muted">
          Tip: take a fresh backup now and then so your latest work is always safe.
        </p>
      </section>
    </div>
  )
}
