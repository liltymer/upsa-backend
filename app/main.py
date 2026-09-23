import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS, IS_DEVELOPMENT
from app.migrate import run_migrations

from app.routes.students import router as students_router
from app.routes.results import router as results_router
from app.routes.gpa import router as gpa_router
from app.routes.dev import router as dev_router
from app.routes.courses import router as courses_router
from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.enrollments import router as enrollments_router
from app.routes.insights import router as insights_router
from app.routes.risk import router as risk_router
from app.routes.trends import router as trends_router
from app.routes.projection import router as projection_router
from app.routes.transcript import router as transcript_router
from app.routes.admin import router as admin_router
from app.routes.announcements import router as announcements_router
from app.routes.password_reset import router as password_reset_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Apply any pending database migrations before serving requests
    run_migrations()
    yield


app = FastAPI(title="GradeIQ UPSA API", version="2.0.0", lifespan=lifespan)

# ================================
# CORS Configuration
# ================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ================================
# Security headers
# ================================

DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if not IS_DEVELOPMENT:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    # The API only serves JSON/PDF; the interactive docs need their CDN assets
    if not request.url.path.startswith(DOCS_PATHS):
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    # Responses carry personal academic data: never cache them in shared caches
    if request.headers.get("authorization"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response

# ================================
# Routers
# ================================

# Seeding / reset routes exist for local development only
if IS_DEVELOPMENT:
    app.include_router(dev_router)

app.include_router(auth_router)
app.include_router(students_router)
app.include_router(enrollments_router)
app.include_router(results_router)
app.include_router(gpa_router)
app.include_router(courses_router)
app.include_router(dashboard_router)
app.include_router(insights_router)
app.include_router(risk_router)
app.include_router(trends_router)
app.include_router(projection_router)
app.include_router(transcript_router)
app.include_router(admin_router)
app.include_router(announcements_router)
app.include_router(password_reset_router)


@app.get("/")
def root():
    return {
        "message": "GradeIQ UPSA API is running",
        "version": app.version,
        "docs": "/docs"
    }


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}
