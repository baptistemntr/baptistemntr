import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker  # type: ignore[attr-defined]
from sqlalchemy.pool import NullPool

Base = declarative_base()

# PostgreSQL en production (même patron que l'agent Agile), SQLite en développement.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./catalogue.db")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=NullPool
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    from catalogue import models  # noqa: F401  (enregistre les tables sur Base)

    Base.metadata.create_all(bind=engine)
