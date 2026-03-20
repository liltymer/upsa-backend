from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine

from app.routes.students import router as students_router
from app.routes.results import router as results_router
from app.routes.gpa import router as gpa_router
from app.routes.dev import router as dev_router
from app.routes.courses import router as courses_router
from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.risk import router as risk_router
from app.routes.trends import router as trends_router
from app.routes.projection import router as projection_router
from app.routes.transcript import router as transcript_router
from app.routes.admin import router as admin_router
from app.routes.announcements import router as announcements_router
from app.routes.password_reset import router as password_reset_router

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="GradeIQ UPSA API")

# ================================
# CORS Configuration
# ================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",                    # Local development
        "https://gradeiq-upsa.vercel.app",          # Vercel production
        "https://gradeiq-upsa-liltymer.vercel.app", # Vercel preview
        "https://upsa-frontend.vercel.app",         # Old frontend if any
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================
# Routers
# ================================

app.include_router(dev_router)
app.include_router(auth_router)
app.include_router(students_router)
app.include_router(results_router)
app.include_router(gpa_router)
app.include_router(courses_router)
app.include_router(dashboard_router)
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
        "version": "1.0.0",
        "docs": "/docs"
    }