"""
MarketLens — Database connection pool for the backend.
Uses a module-level engine singleton for connection reuse.
"""

import os
from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def get_db_engine() -> Engine:
    host     = os.getenv("DB_HOST",     "localhost")
    port     = os.getenv("DB_PORT",     "5432")
    dbname   = os.getenv("DB_NAME",     "marketlens")
    user     = os.getenv("DB_USER",     "marketlens_user")
    password = os.getenv("DB_PASSWORD", "marketlens_pass")

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)


def get_db_session() -> Generator[Session, None, None]:
    engine  = get_db_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
