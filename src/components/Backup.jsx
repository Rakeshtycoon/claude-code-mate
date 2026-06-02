import { useEffect, useRef, useState } from 'react'
import {
  downloadBackup,
  shareBackup,
  parseBackup,
  restoreBackup,
  summarize,
  collectData,
} from '../lib/backup.js'
import {
  getSnapshots,
  addSnapshot,
  deleteSnapshot,
  snapshotAsBackup,
  fileApiSupported,
  fileBackupStatus,
  setupFileBackup,
  disableFileBackup,
  backupToFileNow,
} from '../lib/autobackup.js'

function formatWhen(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function Backup() {
  const fileRef = useRef(null)
  const [message, setMessage] = useState(null) // { type, text }
  const [pending, setPending] = useState(null) // parsed backup awaiting confirm
  const [snapshots, setSnapshots] = useState(() => getSnapshots())
  const [fileStatus, setFileStatus] = useState({ supported: false })

  const liveSummary = summarize(collectData())

  function refreshSnapshots() {
    setSnapshots(getSnapshots())
  }

  async function refreshFileStatus() {
    setFileStatus(await fileBackupStatus())
  }

  useEffect(() => {
    refreshFileStatus()
  }, [])

  /* ----- automatic: file ----- */
  async function enableFileBackup() {
    try {
      await setupFileBackup()
      await refreshFileStatus()
      setMessage({
        type: 'ok',
        text: 'Auto-backup is on. This file will update automatically once a day, and whenever you tap "Back up now".',
      })
    } catch (err) {
      if (err?.name !== 'AbortError') {
        setMessage({ type: 'err', text: 'Could not set up the backup file.' })
      }
    }
  }

  async function backupNow() {
    try {
      await backupToFileNow()
      await refreshFileStatus()
      setMessage({ type: 'ok', text: 'Backup file updated just now.' })
    } catch (err) {
      setMessage({ type: 'err', text: err.message })
    }
  }

  async function turnOffFileBackup() {
    await disableFileBackup()
    await refreshFileStatus()
    setMessage({ type: 'ok', text: 'Auto-backup to file turned off.' })
  }

  /* ----- snapshots ----- */
  function snapshotNow() {
    addSnapshot('manual')
    refreshSnapshots()
    setMessage({ type: 'ok', text: 'Restore point saved.' })
  }

  function restoreSnapshot(snap) {
    if (
      !window.confirm(
        'Restore this point? It will replace the data currently on this device.'
      )
    )
      return
    restoreBackup(snapshotAsBackup(snap), { merge: false })
    window.location.reload()
  }

  function removeSnapshot(id) {
    deleteSnapshot(id)
    refreshSnapshots()
  }

  /* ----- manual export / import ----- */
  function handleExport() {
    try {
      const backup = downloadBackup()
      const s = summarize(backup.data)
      setMessage({
        type: 'ok',
        text: `Backup downloaded — ${s.days} day(s), ${s.goals} goal(s).`,
      })
    } catch {
      setMessage({ type: 'err', text: 'Could not create the backup file.' })
    }
  }

  async function handleShare() {
    try {
      const { shared } = await shareBackup()
      setMessage({
        type: 'ok',
        text: shared
          ? 'Share sheet opened — send it to WhatsApp, Email or Drive.'
          : 'Sharing isn’t available here, so the backup was downloaded instead.',
      })
    } catch {
      setMessage({ type: 'err', text: 'Could not share the backup.' })
    }
  }

  function handleFile(e) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      try {
        setPending(parseBackup(String(reader.result)))
        setMessage(null)
      } catch (err) {
        setPending(null)
        setMessage({ type: 'err', text: err.message })
      }
    }
    reader.onerror = () => setMessage({ type: 'err', text: 'Could not read that file.' })
    reader.readAsText(file)
    e.target.value = ''
  }

  function confirmRestore() {
    try {
      restoreBackup(pending, { merge: false })
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
            Your diary is backed up automatically — no download needed.
          </p>
        </div>
      </header>

      {message && (
        <div className={`banner ${message.type === 'err' ? 'banner-err' : 'banner-ok'}`}>
          {message.text}
        </div>
      )}

      {/* ---- Automatic daily backup (works everywhere) ---- */}
      <section className="card">
        <div className="section-bar">🔄 Automatic daily backup</div>
        <p className="muted backup-desc">
          Every day, the first time you open the app, it saves a restore point
          automatically. You currently have <strong>{snapshots.length}</strong>{' '}
          restore point(s). Newest is kept; up to 14 days are stored.
        </p>
        <div className="link-row" style={{ marginBottom: 12 }}>
          <button className="btn" onClick={snapshotNow}>
            Save a restore point now
          </button>
        </div>
        {snapshots.length === 0 ? (
          <p className="muted">No restore points yet — one will be made today.</p>
        ) : (
          <ul className="snapshot-list">
            {snapshots.map((s) => {
              const sum = summarize(s.data)
              return (
                <li key={s.id}>
                  <span className="snap-when">{formatWhen(s.at)}</span>
                  <span className="tag">{s.kind === 'manual' ? 'manual' : 'daily'}</span>
                  <span className="snap-detail muted">
                    {sum.days} day(s), {sum.goals} goal(s)
                  </span>
                  <span className="snap-actions">
                    <button className="btn small" onClick={() => restoreSnapshot(s)}>
                      Restore
                    </button>
                    <button className="icon-btn" title="Delete" onClick={() => removeSnapshot(s.id)}>
                      ✕
                    </button>
                  </span>
                </li>
              )
            })}
          </ul>
        )}
        <p className="muted small-note">
          Restore points are stored inside this browser, so they protect against
          mistakes — but to be safe if the phone is lost, also turn on the file
          backup below or download a copy now and then.
        </p>
      </section>

      {/* ---- Auto-save to a file (Chrome / Android / desktop) ---- */}
      <section className="card">
        <div className="section-bar">📁 Auto-save to a file</div>
        {!fileStatus.supported ? (
          <p className="muted backup-desc">
            This browser can't auto-save to a file. On iPhone/Safari, use the
            daily restore points above plus the manual backup below (save the
            file to Google Drive). On Chrome or Android Chrome you get automatic
            file saving here.
          </p>
        ) : !fileStatus.enabled ? (
          <>
            <p className="muted backup-desc">
              Pick a backup file once — ideally inside a Google&nbsp;Drive folder
              on your phone. After that it updates automatically once a day, with
              no download and no prompts.
            </p>
            <button className="btn primary" onClick={enableFileBackup}>
              Turn on auto-backup to a file
            </button>
          </>
        ) : (
          <>
            <p className="backup-desc">
              Auto-backup is <strong>on</strong> → <code>{fileStatus.name}</code>
              <br />
              <span className="muted">
                Last saved: {fileStatus.lastBackup || 'today'}
                {!fileStatus.granted && ' (tap "Back up now" to re-allow access)'}
              </span>
            </p>
            <div className="link-row">
              <button className="btn primary" onClick={backupNow}>
                Back up now
              </button>
              <button className="btn" onClick={turnOffFileBackup}>
                Turn off
              </button>
            </div>
          </>
        )}
      </section>

      {/* ---- Manual export / import ---- */}
      <div className="grid-2">
        <section className="card backup-card">
          <h3 className="list-title">⬇️ Download a copy</h3>
          <ul className="backup-stats">
            <li><strong>{liveSummary.days}</strong> daily page(s)</li>
            <li><strong>{liveSummary.goals}</strong> goal(s)</li>
            <li><strong>{liveSummary.monthlyPlans}</strong> monthly plan(s)</li>
          </ul>
          <div className="link-row">
            <button className="btn primary" onClick={handleShare}>
              📤 Share backup
            </button>
            <button className="btn" onClick={handleExport}>
              Download
            </button>
          </div>
          <p className="muted small-note">
            “Share” opens WhatsApp / Email / Drive on your phone so you can send the
            backup to yourself.
          </p>
        </section>

        <section className="card backup-card">
          <h3 className="list-title">⬆️ Restore from a file</h3>
          <p className="muted backup-desc">
            Load a backup file from this device or Google&nbsp;Drive.
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
                This backup has <strong>{pendingSummary.days}</strong> day(s),{' '}
                <strong>{pendingSummary.goals}</strong> goal(s).
              </p>
              <p className="warn">
                ⚠️ This replaces the data on this device and can't be undone.
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
    </div>
  )
}
