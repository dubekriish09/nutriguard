from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import settings

# Use DATABASE_URL from settings (reads from env var / .env)
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

connect_args = {}
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    from models.base import Base
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
