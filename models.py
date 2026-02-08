"""Database models for PhD projects."""

import os
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    Integer,
    Boolean,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DB_URL, DB_PATH

Base = declarative_base()


class PhDProject(Base):
    __tablename__ = "phd_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    university = Column(String(300))
    department = Column(String(300))
    supervisor = Column(String(300))
    region = Column(String(50))  # europe / australia / north_america
    region_cn = Column(String(20))  # 欧陆 / 澳洲 / 北美
    country = Column(String(100))
    funding_type = Column(String(100))  # fully_funded / csc / rolling / position
    discipline = Column(String(200))
    deadline = Column(String(100))  # Keep as string, deadlines vary in format
    description = Column(Text)
    url = Column(String(1000), unique=True, nullable=False)
    source = Column(String(100))  # findaphd / euraxess / scholarshipdb
    is_new = Column(Boolean, default=True)
    collected_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<PhDProject(title='{self.title[:50]}', region='{self.region_cn}')>"


def init_db():
    """Initialize database and create tables."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    engine = create_engine(DB_URL)
    Base.metadata.create_all(engine)
    return engine


def get_session():
    """Get a new database session."""
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    return Session()
