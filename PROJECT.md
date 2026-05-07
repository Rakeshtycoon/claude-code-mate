# Medicare - Medicine Management App

A simple, browser-based medicine management application for tracking prescriptions and medications.

## Features

- **Add Medicine** — Record a new medicine with name, dosage, frequency, and start date
- **Edit Medicine** — Update any existing medicine's details in-place
- **Delete Medicine** — Remove a medicine from the list
- **Persistent Storage** — All data saved to `localStorage`; survives page refresh

## Tech Stack

- Plain HTML5, CSS3, vanilla JavaScript
- No build tools or dependencies required
- Single-file app (`index.html`)

## Getting Started

Open `index.html` in any modern browser. No server required.

## Data Model

Each medicine entry has:

| Field      | Type   | Description                          |
|------------|--------|--------------------------------------|
| id         | string | Auto-generated unique identifier     |
| name       | string | Medicine name                        |
| dosage     | string | Dosage amount and unit (e.g. 500 mg) |
| frequency  | string | How often taken (e.g. Twice daily)   |
| startDate  | string | ISO date when course began           |
| notes      | string | Optional additional notes            |

## File Structure

```
.
├── index.html   # Main application (UI + logic)
└── PROJECT.md   # This file
```
