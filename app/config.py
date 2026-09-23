import os

from dotenv import load_dotenv

load_dotenv()

# ================================
# ENVIRONMENT
# ================================

# "development" enables the /dev seeding routes. Anything else is treated as production.
ENVIRONMENT = os.getenv("ENVIRONMENT", "production").strip().lower()
IS_DEVELOPMENT = ENVIRONMENT == "development"

# ================================
# FRONTEND / CORS
# ================================

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://gradeiq-upsa.vercel.app").rstrip("/")

# Comma-separated list, e.g. "https://gradeiq-upsa.vercel.app,http://localhost:5173"
ALLOWED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        f"{FRONTEND_URL},http://localhost:5173",
    ).split(",")
    if origin.strip()
]

# ================================
# SECURITY
# ================================

PASSWORD_MIN_LENGTH = 8
