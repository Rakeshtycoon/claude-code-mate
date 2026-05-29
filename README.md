# Business Diary

A personal-use web app that digitizes the **Progress Alliance** business diary —
daily tasks, goals, monthly planning, and sales tracking, all in one place.

Modeled directly on the printed diary's structure, it runs entirely in your
browser. There is **no server and no account**: all your data is saved locally
in the browser via `localStorage`, so it stays private to your device and works
offline.

## Features

Each section mirrors a part of the physical diary:

| Section | What it covers |
| --- | --- |
| **Dashboard** | Daily snapshot — morning mantras, today's tasks, goals completed, month's sales target, and your vision. |
| **Daily** | The core daily page: Morning Mantras checklist, Month & Today targets (Sales / Collection), and task lists — Yearly-Goal Actions, Visit / One-to-One / Zoom, Follow-ups, Quotation / Inquiry, Operations, Business, Team & Customer Follow, Other, Family / Other. Navigate by date. |
| **Goals** | "My Goals in [year]" across 6 categories — Business, Finance, Family, Health, Progress Alliance, Crazy — each item cycling through the diary's statuses: To Start → OK → Delay → Stuck → Cancel. |
| **Monthly** | *Monthly Plan* (last year vs this year for Sales/Profit/Purchase/Expense/Other, Comparison, Target, Achieved, % achieved, missed actions) and *Sales Data Analysis* (month-by-month Apr→Mar table with auto-calculated %). |
| **Planner** | A monthly calendar with a note per day, plus "My Planning for Next Month". |
| **Lists** | Daily Rituals, Empowering Lines & Quotes, and "20 Things Before I Die". |
| **Profile** | Company & personal details, plus Vision, Mission and Core Values. |
| **Backup** | Download your whole diary as one `.json` file, and restore it on any device — including via Google Drive. |

## Backup

The **Backup** section keeps your diary safe with three layers. Since the app
runs only in the browser, it can't wake up on its own while closed — so the
automatic backup runs **the first time you open the app each day** (which, for
a morning routine, means roughly once every morning).

1. **Automatic daily restore points** — every day on first open, a snapshot is
   saved silently inside the browser (up to 14 kept). Restore any of them with
   one tap. No download needed. Great for undoing mistakes.
2. **Auto-save to a file** *(Chrome / Edge / Android Chrome)* — pick a backup
   file once (ideally in a Google Drive folder); it then updates automatically
   once a day and whenever you tap **Back up now**, with no prompts. This is the
   layer that protects you if the phone is lost.
3. **Manual download / restore** — download a `.json` copy anytime, or restore
   one from this device or Google Drive. Works in every browser, including
   iPhone/Safari.

### Moving to a new phone
Save (or auto-save) the backup file to **Google Drive**, download it on the new
phone, then open **Backup → Choose backup file…** and confirm. Your old diary
comes back (this replaces the data on that device).

> Note: true background backup at a fixed time while the app is closed would
> require installing it as a PWA (Chrome's Periodic Background Sync) or a small
> server. The current approach is server-free and private.

## Tech stack

- [React 18](https://react.dev/) + [Vite](https://vite.dev/) — fast, modern single-page app
- Browser `localStorage` for persistence (no backend required)
- No external UI libraries — plain CSS, styled after the diary's blue/orange theme

## Getting started

```bash
npm install      # install dependencies
npm run dev      # start the dev server (opens http://localhost:5173)
```

To build a production bundle and preview it:

```bash
npm run build    # outputs to dist/
npm run preview  # serve the built app locally
```

## Where your data lives

Everything you type is stored in your browser under keys prefixed with `bd.`
(e.g. `bd.days`, `bd.goals`, `bd.profile`). Clearing your browser data — or
switching to a different browser/device — will start you fresh. To move your
diary between devices in the future, an export/import feature is a natural next
step.

## Project structure

```
src/
  App.jsx                 # navigation shell + view routing
  main.jsx                # React entry point
  index.css               # all styling
  hooks/
    useLocalStorage.js    # persist state to localStorage
  lib/
    format.js             # id, date and currency helpers
  components/
    Dashboard.jsx         # overview
    Daily.jsx             # daily page (mantras, targets, task lists)
    Goals.jsx             # yearly goals with status cycling
    Monthly.jsx           # monthly plan + sales analysis
    Planner.jsx           # calendar + next-month planning
    Lists.jsx             # rituals, quotes, bucket list
    Profile.jsx           # company/personal details + vision
    EditableList.jsx      # reusable add/check/delete list
```

> Built for personal use. "I am my word."
