import os
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator

DATABASE_URL = "sqlite:///./database.db"

# connect_args={"check_same_thread": False} is required only for SQLite.
engine = create_engine(
    DATABASE_URL, 
    echo=False, 
    connect_args={"check_same_thread": False}
)

def init_db():
    from models import User, Profile, SkillMaster, UserSkill, Roadmap, RoadmapNode, Resume, UserProjectProgress, LearningSession, AIConversation, AIMessage
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
