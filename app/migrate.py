import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.database import engine

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def alembic_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    config.attributes["skip_logging_config"] = True
    return config


def run_migrations(revision: str = "head") -> None:
    """Brings the database schema up to date. Safe to run on every start."""
    config = alembic_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, revision)
    logger.info("Database schema is up to date (%s)", revision)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()
