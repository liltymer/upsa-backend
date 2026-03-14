from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine

from app.routes.students import router as students_router
from app.routes.results import router as results_router
from app.routes.gpa import router as gpa_router
from app.routes.dev import router as dev_router
from app.routes.courses import router as courses_router
from app.routes.auth import router as auth_router 
from app.routes.dashboard import router as dashboard_router  # NEW
from app.routes.risk import router as risk_router
from app.routes.trends import router as trends_router
from app.routes.projection import router as projection_router
from app.routes.transcript import router as transcript_router

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="UPSA Smart Academic Platform API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(dev_router)
app.include_router(auth_router)  # NEW - authentication routes
app.include_router(students_router)
app.include_router(results_router)
app.include_router(gpa_router)
app.include_router(courses_router)
app.include_router(dashboard_router)
app.include_router(risk_router)
app.include_router(trends_router)
app.include_router(projection_router)
app.include_router(transcript_router)


@app.get("/")
def root():
    return {"message": "UPSA API running"}