# Family Medicare — AI-Powered Medicine Manager

A browser-based family medicine management application enhanced with Claude AI for intelligent medicine recognition, drug interaction checking, and an AI chat assistant.

## Features

### Core Medicine Management
- **Add Medicine** — Record medicine with name, dosage, frequency, start date, and notes
- **Edit Medicine** — Update existing medicine details via modal
- **Delete Medicine** — Remove medicines with confirmation
- **Persistent Storage** — All data saved to `localStorage`; survives page refresh
- **Responsive Design** — Works on desktop, tablet, and mobile

### AI Features (powered by Claude claude-sonnet-4-6)
- **AI Auto-Fill** — Describe a medicine in plain language; AI extracts and fills the form automatically
- **AI Chat Assistant** — Ask questions about your medicines, dosage, side effects, and schedules
- **Drug Interaction Checker** — Check interactions between any two medicines with severity levels (safe / warn / danger)
- **Medicine Context** — AI assistant is aware of all medicines currently in your list

## Tech Stack

- Plain HTML5, CSS3, vanilla JavaScript
- Claude API (`claude-sonnet-4-6`) via direct fetch calls
- No build tools or external dependencies
- Single-file app (`index.html`)

## Getting Started

1. Open `index.html` in any modern browser (no server required)
2. Enter your Anthropic API key in the **Claude AI Setup** panel (stored locally in `localStorage`)
3. Start managing medicines and using AI features

## Data Model

| Field      | Type   | Description                          |
|------------|--------|--------------------------------------|
| id         | string | Auto-generated unique identifier     |
| name       | string | Medicine name                        |
| dosage     | string | Dosage amount and unit (e.g. 500 mg) |
| frequency  | string | How often taken (e.g. Twice daily)   |
| startDate  | string | ISO date when course began           |
| notes      | string | Optional additional notes            |

## AI Features Detail

### AI Auto-Fill
Describe a medicine in natural language and AI will parse and populate:
- Medicine name
- Dosage
- Frequency (mapped to dropdown options)
- Start date
- Notes

Example: *"Paracetamol 500mg twice daily for fever, started today, take with food"*

### AI Chat Assistant
Quick suggestion chips for common queries:
- Side effects
- Drug interactions
- Food/timing guidelines
- Medicine summary

The AI is aware of your full medicine list and can answer context-aware questions.

### Drug Interaction Checker
Returns a structured result with:
- **Severity level**: safe / warn / danger
- **Summary**: 1-2 sentence overview
- **Details**: Clinical recommendation

## File Structure

```
.
├── index.html    # Main application (UI + AI logic + medicine management)
└── PROJECT.md    # This file
```

## Privacy

- API key is stored in browser `localStorage` only
- Medicine data never leaves the browser
- Claude API calls are made directly from your browser to Anthropic's servers
