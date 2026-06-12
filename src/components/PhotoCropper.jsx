import { useEffect, useRef, useState } from 'react'

/**
 * A simple square photo cropper with zoom (slider / + −) and drag-to-pan.
 * No external library. Calls onSave with a cropped JPEG data URL.
 *
 * @param {object}   props
 * @param {string}   props.src       Source image data URL.
 * @param {Function} props.onSave    Receives the cropped data URL.
 * @param {Function} props.onCancel
 * @param {number}   [props.output]  Output square size in px (default 320).
 */
export default function PhotoCropper({ src, onSave, onCancel, output = 320 }) {
  const VIEW = 280 // on-screen square size
  const [img, setImg] = useState(null)
  const [zoom, setZoom] = useState(1)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const baseRef = useRef(1)
  const drag = useRef(null)

  // Load the image and fit it to "cover" the viewport at zoom = 1.
  useEffect(() => {
    const image = new Image()
    image.onload = () => {
      const base = VIEW / Math.min(image.width, image.height)
      baseRef.current = base
      const dispW = image.width * base
      const dispH = image.height * base
      setImg(image)
      setZoom(1)
      setOffset({ x: (VIEW - dispW) / 2, y: (VIEW - dispH) / 2 })
    }
    image.src = src
  }, [src])

  function clamp(off, z) {
    const s = baseRef.current * z
    const dispW = img.width * s
    const dispH = img.height * s
    return {
      x: Math.min(0, Math.max(VIEW - dispW, off.x)),
      y: Math.min(0, Math.max(VIEW - dispH, off.y)),
    }
  }

  function changeZoom(z) {
    if (!img) return
    const nz = Math.max(1, Math.min(4, z))
    // Keep the viewport centre fixed while zooming.
    const s0 = baseRef.current * zoom
    const s1 = baseRef.current * nz
    const cx = (VIEW / 2 - offset.x) / s0
    const cy = (VIEW / 2 - offset.y) / s0
    const nx = VIEW / 2 - cx * s1
    const ny = VIEW / 2 - cy * s1
    setZoom(nz)
    setOffset(clamp({ x: nx, y: ny }, nz))
  }

  function onDown(e) {
    const p = e.touches ? e.touches[0] : e
    drag.current = { sx: p.clientX, sy: p.clientY, ox: offset.x, oy: offset.y }
  }
  function onMove(e) {
    if (!drag.current || !img) return
    const p = e.touches ? e.touches[0] : e
    const nx = drag.current.ox + (p.clientX - drag.current.sx)
    const ny = drag.current.oy + (p.clientY - drag.current.sy)
    setOffset(clamp({ x: nx, y: ny }, zoom))
  }
  function onUp() {
    drag.current = null
  }

  function save() {
    if (!img) return
    const s = baseRef.current * zoom
    const sourceSide = VIEW / s
    const sx = -offset.x / s
    const sy = -offset.y / s
    const canvas = document.createElement('canvas')
    canvas.width = output
    canvas.height = output
    const ctx = canvas.getContext('2d')
    ctx.drawImage(img, sx, sy, sourceSide, sourceSide, 0, 0, output, output)
    onSave(canvas.toDataURL('image/jpeg', 0.85))
  }

  const s = img ? baseRef.current * zoom : 1

  return (
    <div className="cropper-overlay" onMouseUp={onUp} onMouseLeave={onUp}>
      <div className="cropper-modal">
        <h3 className="list-title">Adjust photo</h3>
        <div
          className="cropper-stage"
          style={{ width: VIEW, height: VIEW }}
          onMouseDown={onDown}
          onMouseMove={onMove}
          onTouchStart={onDown}
          onTouchMove={onMove}
          onTouchEnd={onUp}
        >
          {img && (
            <img
              className="cropper-img"
              src={src}
              alt=""
              draggable={false}
              style={{
                width: img.width * s,
                height: img.height * s,
                transform: `translate(${offset.x}px, ${offset.y}px)`,
              }}
            />
          )}
          <div className="cropper-ring" />
        </div>

        <div className="cropper-zoom">
          <button type="button" className="btn small" onClick={() => changeZoom(zoom - 0.25)}>−</button>
          <input
            type="range"
            min="1"
            max="4"
            step="0.01"
            value={zoom}
            onChange={(e) => changeZoom(Number(e.target.value))}
          />
          <button type="button" className="btn small" onClick={() => changeZoom(zoom + 0.25)}>+</button>
        </div>

        <div className="cropper-actions">
          <button type="button" className="btn" onClick={onCancel}>Cancel</button>
          <button type="button" className="btn primary" onClick={save}>Use photo</button>
        </div>
      </div>
    </div>
  )
}
