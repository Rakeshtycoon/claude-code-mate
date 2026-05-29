// Build a single self-contained HTML file from the Vite production build.
// All JS and CSS are inlined so the result opens directly from the file system
// (no server, no install) — handy for testing and for wrapping into an APK.
//
// Usage: npm run build:single   (runs `vite build` first, then this script)

import { readFileSync, writeFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

const dist = 'dist'
const assets = join(dist, 'assets')
const files = readdirSync(assets)

const jsFile = files.find((f) => f.endsWith('.js'))
const cssFile = files.find((f) => f.endsWith('.css'))

if (!jsFile || !cssFile) {
  console.error('Could not find built JS/CSS in dist/assets. Run `vite build` first.')
  process.exit(1)
}

const js = readFileSync(join(assets, jsFile), 'utf8')
const css = readFileSync(join(assets, cssFile), 'utf8')
const favicon = readFileSync(join(dist, 'favicon.svg'), 'utf8')
const faviconData = `data:image/svg+xml;base64,${Buffer.from(favicon).toString('base64')}`

const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <meta name="theme-color" content="#1e3a8a" />
    <meta name="description" content="Business Diary — daily journal, goals, planning and sales tracking." />
    <link rel="icon" type="image/svg+xml" href="${faviconData}" />
    <title>Business Diary</title>
    <style>${css}</style>
  </head>
  <body>
    <div id="root"></div>
    <script type="module">
${js}
    </script>
  </body>
</html>
`

const out = 'business-diary-test.html'
writeFileSync(out, html)
console.log(`Wrote ${out} (${(html.length / 1024).toFixed(0)} KB) — open it in any browser.`)
