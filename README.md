# GradeIQ UPSA — Backend

FastAPI service behind the GradeIQ UPSA academic platform: student accounts, result entry,
GPA/CGPA calculation on the official UPSA scale, risk analysis, CGPA projection, PDF transcripts
and an admin console.

## Stack

- Python 3.13, FastAPI, SQLAlchemy 2
- PostgreSQL (Neon) in production, SQLite for local runs and tests
- JWT auth (python-jose), bcrypt password hashing
- Resend for password-reset email, ReportLab for PDF transcripts

## Local setup

```bash
python -m venv venv
venv\Scripts\activate            # Windows  (source venv/bin/activate on macOS/Linux)
pip install -r requirements-dev.txt

cp .env.example .env             # then edit values
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Configuration

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | yes | Postgres URL, or `sqlite:///./local.db` locally |
| `SECRET_KEY` | yes | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | Token lifetime, default 60 |
| `ENVIRONMENT` | no | `development` mounts the admin-only `/dev` seed/reset routes. Defaults to `production` |
| `FRONTEND_URL` | no | Used in password-reset links |
| `ALLOWED_ORIGINS` | no | Comma-separated CORS allow-list. Defaults to `FRONTEND_URL` + `http://localhost:5173` |
| `RESEND_API_KEY` | for email | Password-reset emails |
| `EMAIL_FROM` | for email | Sender on a Resend-verified domain (the default test sender only reaches the Resend account owner) |

## Database migrations

Schema changes are managed with Alembic (`migrations/`). Pending migrations run
automatically when the app starts, so a normal Render deploy applies them.

```bash
python -m app.migrate                      # apply manually
alembic revision -m "describe change"      # new migration (edit the generated file)
alembic downgrade -1                       # roll back one step
```

## Programmes and top-up students

A `Student` is a login account. Each UPSA programme the student has been on is an
`Enrollment` with its own index number, award type (diploma/degree), level and
results. GPA, risk, trends, projection and transcripts are always computed for one
enrollment — a diploma CGPA and a top-up degree CGPA are never combined.

- `POST /enrollments/top-up` — start a degree with the new index number; the diploma is kept as completed
- `POST /enrollments/previous` — record a programme completed earlier
- `POST /enrollments/link-account` — merge a second account created for the top-up
- `POST /results/move` — move results between programmes
- Academic endpoints accept `?enrollment_id=`; default is the current programme
- Login accepts the email or any of the student's index numbers

GPAs are truncated to two decimals, matching UPSA transcripts (2.825 → 2.82).

## Tests

```bash
pytest
```

Tests run against a throwaway SQLite database and never send real email.

## Project layout

```
app/
  main.py        app, CORS, security headers, router registration
  config.py      environment-driven settings
  migrate.py     runs Alembic migrations on startup
  database.py    engine / session
  models/        SQLAlchemy models
  schemas/       Pydantic request/response models
  routes/        API routers
  services/      auth, email, PDF, analytics engines
  utils/         grading scale and GPA maths
migrations/      Alembic migrations
tests/
```

## Creating an admin

Register normally, then set `role = 'admin'` on that row in the `students` table.
