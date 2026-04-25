from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

# Pydantic v2's AnyUrl gives a Url object; SQLAlchemy expects a plain string.
engine = create_engine(str(settings.DATABASE_URL), echo=False, future=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

