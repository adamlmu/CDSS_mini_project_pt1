from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import DATABASE_URL

# Async engine ל‑SQLite
engine = create_async_engine(DATABASE_URL, future=True, echo=False)

# הבסיס לכל המודלים
Base = declarative_base()

# SessionLocal מסוג AsyncSession
SessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
