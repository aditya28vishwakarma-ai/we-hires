# WeHires — Student Recruitment Tracker

A lightweight, full-stack Applicant Tracking System (ATS) built with **Flask** and **vanilla HTML/CSS/JS**, designed to manage student recruitment pipelines from application through to offer or rejection.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [File Structure](#file-structure)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Hiring Pipeline & Gate Logic](#hiring-pipeline--gate-logic)
- [Data Schema](#data-schema)
- [Contributing](#contributing)

---

## Overview

WeHires is a mini ATS built for campus recruitment scenarios. It provides two distinct user experiences:

- **Recruiters** log in, manage a drag-and-drop Kanban board, review analytics, and track team activity.
- **Candidates (Students)** visit a self-service portal to apply for roles and check their application status using their name and roll number.

All data is stored in flat JSON files — no database setup required — making it trivial to run locally or deploy to any basic hosting environment.

---

## Features

### Recruiter Side
- **Recruiter Login** — Name-based session login that logs every recruiter who signs in, with timestamps and login counts tracked in `recruiter_log.json`.
- **Dashboard** — Team overview with live stats (total candidates, in-progress, offered, rejected), a real-data *Feedback Pending* widget showing all candidates currently in the Technical Test stage awaiting a decision, active role summaries, and a hiring team activity feed listing all recruiters who have logged in.
- **Kanban Board** — Drag-and-drop candidate cards across five pipeline stages: `Applied → Interviewing → Technical Test → Offered / Rejected`. Cards show initials, role, priority badge, and time indicator. Full detail view on click.
- **Add Candidate** — Recruiters can add candidates directly from the board via a modal form.
- **Analytics** — Pipeline velocity chart, stage distribution, offer rate, rejection rate, average interview score, and average technical test score — all computed live from `candidates.json`.
- **Settings** — Portal-wide settings page including a *Switch to Guest* option.

### Candidate Side
- **Apply** — Self-registration form: name, roll number, and role selection. Duplicate applications (same roll number + same role) are blocked.
- **My Status** — Candidates look up their application status by entering their name and roll number. Scores are hidden while in early stages (`Applied`, `Interviewing`) and revealed once the candidate reaches `Technical Test` or later.

### Business Logic & Gate Rules
- **Sequential pipeline** — candidates cannot skip stages (e.g. cannot jump from `Applied` directly to `Technical Test`).
- **Auto-rejection on low scores** — interview score below 50 → auto-rejected; technical test score below 70 → auto-rejected.
- **Permanent lock** — once a candidate is `Rejected`, their card is locked and cannot be moved again.
- **Manual rejection** — recruiters can manually reject a candidate from any unlocked stage.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask |
| Templating | Jinja2 |
| Frontend | HTML5, Vanilla CSS, Vanilla JS |
| Styling | Material Design 3 color tokens, Inter font, Material Symbols icons |
| Data Storage | JSON flat files (`candidates.json`, `recruiter_log.json`) |
| Session Management | Flask server-side sessions |

---

## File Structure

```
we-hires/
│
├── app.py                        # Flask application — all routes and business logic
│
├── candidates.json               # Persistent store for all candidate records
├── recruiter_log.json            # Auto-updated log of recruiter logins (name, timestamp, count)
│
├── static/
│   ├── portal.css                # Shared design system — MD3 color tokens, sidebar, header,
│   │                             #   nav, layout primitives used across recruiter pages
│   ├── recruiter_dashboard.css   # Styles scoped to the recruiter dashboard page
│   ├── script.js                 # Kanban drag-and-drop logic, modal handlers, API calls
│   └── style.css                 # Candidate-facing portal styles (candidate.html)
│
├── templates/
│   ├── recruiter_login.html      # Recruiter name-based login page (entry point → /login)
│   ├── recruiter_dashboard.html  # Dashboard: stats, feedback pending, team activity, roles
│   ├── candidates_board.html     # Kanban board with drag-and-drop stage management
│   ├── analytics.html            # Pipeline velocity, score averages, stage breakdown charts
│   ├── settings.html             # Settings page (Switch to Guest, portal preferences)
│   ├── candidate.html            # Student self-service portal (Apply + My Status tabs)
│   └── index.html                # Root redirect shell (points to /login)
│
├── .gitignore                    # Standard Python/Flask gitignore
└── README.md                     # This file
```

---

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/aditya28vishwakarma-ai/we-hires.git
cd we-hires
```

**2. Create and activate a virtual environment**

```bash
# Create
python -m venv venv

# Activate — macOS / Linux
source venv/bin/activate

# Activate — Windows
venv\Scripts\activate
```

**3. Install dependencies**

```bash
pip install Flask
```

**4. Run the app**

```bash
python app.py
```

The app will start on `http://localhost:5000`.

### First-time use

| URL | Who uses it |
|---|---|
| `http://localhost:5000/login` | Recruiter login (enter any name) |
| `http://localhost:5000/dashboard` | Recruiter dashboard |
| `http://localhost:5000/candidates-board` | Kanban board |
| `http://localhost:5000/analytics` | Analytics page |
| `http://localhost:5000/settings` | Settings |
| `http://localhost:5000/candidate` | Student self-service portal |

> `candidates.json` is pre-seeded with sample data. Delete its contents and replace with `[]` to start fresh.

---

## API Reference

All API endpoints accept and return `application/json`.

### Candidates

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/candidates` | Returns the full list of all candidates |
| `POST` | `/api/candidates` | Adds a new candidate (recruiter-side) |
| `POST` | `/api/candidates/<id>/move` | Moves a candidate to a new stage (with gate logic) |

#### `POST /api/candidates` — Request body

```json
{
  "name": "Alex Johnson",
  "roll_number": "CS2026-08",
  "role": "Frontend Developer"
}
```

#### `POST /api/candidates/<id>/move` — Request body

```json
{
  "target_stage": "Technical Test",
  "interview_score": 75
}
```

```json
{
  "target_stage": "Offered",
  "tech_score": 82
}
```

### Student Portal

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/apply` | Student self-applies for a role |
| `POST` | `/api/result` | Student checks their application status |

#### `POST /api/apply` — Request body

```json
{
  "name": "Priya Nair",
  "roll_number": "CS2026-10",
  "role": "Data Analyst"
}
```

#### `POST /api/result` — Request body

```json
{
  "name": "Priya Nair",
  "roll_number": "CS2026-10"
}
```

### Recruiter Log

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/recruiter-log` | Returns list of all recruiters who have logged in |

---

## Hiring Pipeline & Gate Logic

```
Applied ──► Interviewing ──► Technical Test ──► Offered
                │                   │
                ▼                   ▼
            Rejected (auto,      Rejected (auto,
            score < 50)          score < 70)

Any stage ──► Rejected (manual, recruiter decision)
```

| Transition | Requirement | Auto-reject threshold |
|---|---|---|
| Interviewing → Technical Test | `interview_score` (0–100) required | Score **< 50** → auto-rejected |
| Technical Test → Offered | `tech_score` (0–100) required | Score **< 70** → auto-rejected |
| Any → Rejected | Manual recruiter action | Card permanently locked |

**Rules enforced server-side:**
- Stages cannot be skipped — a candidate in `Applied` cannot be moved directly to `Technical Test`.
- Once `is_locked` is `true` (after any rejection), no further moves are permitted regardless of who calls the API.
- Score fields (`interview_score`, `tech_score`) are hidden from the candidate-facing status lookup while the candidate is still in `Applied` or `Interviewing`.

---

## Data Schema

### `candidates.json` — candidate record

```json
{
  "id": 1,
  "name": "Travis Scott",
  "roll_number": "CS2026-01",
  "role": "Software Engineer",
  "stage": "Technical Test",
  "interview_score": 72,
  "tech_score": null,
  "rejection_reason": null,
  "is_locked": false
}
```

| Field | Type | Description |
|---|---|---|
| `id` | integer | Auto-incremented unique identifier |
| `name` | string | Candidate full name |
| `roll_number` | string | Unique student roll number (uppercased on write) |
| `role` | string | One of the five valid roles |
| `stage` | string | Current pipeline stage |
| `interview_score` | integer \| null | Score from interview round (0–100) |
| `tech_score` | integer \| null | Score from technical test (0–100) |
| `rejection_reason` | string \| null | Populated on rejection (auto or manual) |
| `is_locked` | boolean | `true` once rejected — blocks all further moves |

### `recruiter_log.json` — recruiter login entry

```json
{
  "name": "Jane Recruiter",
  "initials": "JR",
  "last_login": "2026-06-14T09:15:00",
  "login_count": 5
}
```

### Valid roles

```
Software Engineer
Frontend Developer
Backend Developer
Data Analyst
DevOps Engineer
```

---

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Open a Pull Request

---

*Built with Flask · Styled with Material Design 3 tokens · No database required*