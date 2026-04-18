# GradeIQ UPSA — Backend

The REST API powering GradeIQ UPSA. Built with FastAPI and PostgreSQL, it handles student authentication, academic data management, admin operations, and transactional email delivery via Resend.

![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi) ![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?style=flat&logo=postgresql) ![Deployed on Render](https://img.shields.io/badge/Deployed-Render-46E3B7?style=flat&logo=render)

---

## Features

- JWT-based authentication with email verification
- Password reset via time-limited email tokens (Resend API)
- Student profile management
- Grade and course data endpoints
- Admin routes for managing students and results
- SQLAlchemy ORM with Alembic migrations

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Language | Python 3.11 |
| ORM | SQLAlchemy |
| Database | PostgreSQL (Neon) |
| Email | Resend API |
| Deployment | Render |

---

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL database (local or Neon)
- Resend API key

### Installation

```bash
# Clone the repository
git clone https://github.com/liltymer/upsa-backend.git
cd upsa-backend

# virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# environment file
cp .env.example .env


# Run database migrations
alembic upgrade head

# Start the development server
uvicorn main:app --reload
```

The API will run at `http://localhost:8000`  
Interactive docs available at `http://localhost:8000/docs`

---

## Environment Variables

```env
DATABASE_URL=**********
SECRET_KEY=**********
RESEND_API_KEY= **********
FRONTEND_URL=https://github.com/liltymer/upsa-frontend
```

---

## Project Structure

```
├── main.py              # App entry point
├── models/              # SQLAlchemy database models
├── routers/             # API route handlers
├── schemas/             # Pydantic request/response schemas
├── services/            # Business logic layer
├── utils/               # Helper functions (auth, email, etc.)
└── alembic/             # Database migration files
```

---

## API Documentation

Once running, visit `/docs` for the full interactive Swagger UI with all available endpoints.

---

## Related

- [GradeIQ Frontend](https://github.com/liltymer/upsa-frontend) — React 19 + Vite client

---

## Author

**Ahenkora** — IT Management Student & Fullstack Developer  
[LinkedIn](https://www.linkedin.com/in/ahenkora-joshua-owusu-42a691320) · [GitHub](https://github.com/liltymer)
