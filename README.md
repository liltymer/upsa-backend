# GradeIQ UPSA — Backend

The REST API powering GradeIQ UPSA. Built with FastAPI and PostgreSQL, it handles student authentication, academic records for every UPSA programme a student has been on (including diploma → degree top-ups), GPA analytics, PDF transcripts, admin operations, and transactional email via Resend.

![FastAPI](https://img.shields.io/badge/FastAPI-0.128-009688?style=flat&logo=fastapi) ![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat&logo=python) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?style=flat&logo=postgresql) ![Deployed on Render](https://img.shields.io/badge/Deployed-Render-46E3B7?style=flat&logo=render)

---

## Features

- JWT authentication — sign in with email or any index number the student has held
- Password reset via time-limited, hashed email tokens (Resend API)
- Multiple programmes per student: a top-up student keeps their completed diploma
  (old index number, final CGPA) alongside their degree (new index number, fresh CGPA)
- Official UPSA grading: diploma (Distinction / Credit / Pass) and degree (First Class …) bands,
  GPAs truncated to 2 decimals exactly like UPSA transcripts
- GPA history, trends, risk analysis, CGPA simulator and target-grade calculator
- Unofficial transcript PDF in the UPSA transcript layout (TCR / TGP / GPA / CGPA)
- Admin routes for students, analytics, announcements and the course catalogue
- Rate limiting, security headers and Alembic migrations applied on startup

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Language | Python 3.13 |
| ORM / Migrations | SQLAlchemy 2 + Alembic |
| Database | PostgreSQL (Neon); SQLite for local runs and tests |
| Email | Resend API |
| PDF | ReportLab |
| Deployment | Render |

---

## Getting Started

### Prerequisites
- Python 3.13
- A database: SQLite works for local development; PostgreSQL (Neon) in production
- Resend API key (only needed for password-reset emails)

### Installation

```bash
# Clone the repository
git clone https://github.com/liltymer/upsa-backend.git
cd upsa-backend

# Virtual environment
python -m venv venv
source venv/bin/activate          # On Windows: venv\Scripts\activate

# Install dependencies (app + test tools)
pip install -r requirements-dev.txt

# Environment file — then edit the values
cp .env.example .env

# Start the development server (pending migrations run automatically on startup)
uvicorn app.main:app --reload
```

The API will run at `http://localhost:8000`
Interactive docs are at `http://localhost:8000/docs`

> Keep `DATABASE_URL=sqlite:///./local.db` in your local `.env`. Never point a local
> run at the production database — the app applies migrations when it starts.

---

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | yes | Postgres URL, or `sqlite:///./local.db` locally |
| `SECRET_KEY` | yes | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | Token lifetime, default 60 |
| `ENVIRONMENT` | no | `development` mounts the admin-only `/dev` seed/reset routes. Defaults to `production` |
| `FRONTEND_URL` | no | Live frontend, e.g. `https://gradeiq-upsa.vercel.app` — used in reset links and CORS |
| `ALLOWED_ORIGINS` | no | Comma-separated CORS allow-list. Defaults to `FRONTEND_URL` + `http://localhost:5173` |
| `RESEND_API_KEY` | for email | Password-reset emails |
| `EMAIL_FROM` | for email | Sender on a Resend-verified domain (the default test sender only reaches the Resend account owner) |

---

## Database Migrations

Schema changes are managed with Alembic (`migrations/`). Pending migrations run
automatically when the app starts, so a normal Render deploy applies them.

```bash
python -m app.migrate                      # apply manually
alembic revision -m "describe change"      # new migration (edit the generated file)
alembic downgrade -1                       # roll back one step
```

---

## Programmes and Top-up Students

A `Student` is a login account. Each UPSA programme the student has been on is an
`Enrollment` with its own index number, award type (diploma/degree), level and
results. GPA, risk, trends, projection and transcripts are always computed for one
enrollment — a diploma CGPA and a top-up degree CGPA are never combined.

- `POST /enrollments/top-up` — start a degree with the new index number; the diploma is kept as completed
- `POST /enrollments/previous` — record a programme completed earlier
- `POST /enrollments/link-account` — merge a second account created for the top-up
- `POST /results/move` — move results between programmes
- Academic endpoints accept `?enrollment_id=`; default is the current programme

---

## Admin: Reset a Student's Password

For a student who cannot receive the reset email:

```bash
python -m app.reset_password student@example.com
```

Run it from the project root with the virtualenv active and `DATABASE_URL`
pointing at the database you mean to change.

---

## Tests

```bash
pytest          # throwaway SQLite database, no real email sent
ruff check .
```

GitHub Actions runs both on every push and pull request.

---

## Project Structure

```
app/
  main.py            app, CORS, security headers, router registration
  config.py          environment-driven settings
  migrate.py         runs Alembic migrations on startup
  database.py        engine / session
  models/            SQLAlchemy models (Student, Enrollment, Result, …)
  schemas/           Pydantic request/response schemas
  routes/            API route handlers
  services/          auth, enrollments, email, PDF, analytics engines
  utils/             UPSA grading scale and GPA maths
  reset_password.py  admin password-reset script
migrations/          Alembic migration files
tests/               pytest suite
```

---

## Creating an Admin

Register normally, then set `role = 'admin'` on that row in the `students` table.

---

## Related

- [GradeIQ Frontend](https://github.com/liltymer/upsa-frontend) — React 19 + Vite client

---

## Author

**Ahenkora** — IT Management Student & Fullstack Developer
[LinkedIn](https://www.linkedin.com/in/ahenkora-joshua-owusu-42a691320) · [GitHub](https://github.com/liltymer)
