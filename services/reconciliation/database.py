from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://payment_user:secure_password_123@postgres_db:5432/payment_gateway",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

Base = declarative_base()


def init_db() -> None:
    # Import models here to register metadata before create_all
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
