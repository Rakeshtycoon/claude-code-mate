// Rasterize public/icon.svg into the PNG icons the PWA needs.
// Run in CI (where `sharp` is installed): node scripts/icons.mjs
import sharp from 'sharp'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const svg = readFileSync(new URL('../public/icon.svg', import.meta.url))
const dir = new URL('../public/', import.meta.url)

const targets = [
  [180, 'apple-touch-icon.png'],
  [192, 'pwa-192.png'],
  [512, 'pwa-512.png'],
]

for (const [size, name] of targets) {
  const out = fileURLToPath(new URL(name, dir))
  await sharp(svg, { density: 384 })
    .resize(size, size, { fit: 'cover' })
    .png()
    .toFile(out)
  console.log('wrote', name, size + 'px')
}
