from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, JSON

class User(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(default="STUDENT")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Profile(SQLModel, table=True):
    user_id: str = Field(primary_key=True, foreign_key="user.id")
    full_name: str
    academic_level: str = Field(default="UNDERGRADUATE") # HIGH_SCHOOL, UNDERGRADUATE, POSTGRADUATE, SELF_LEARNER
    institution: Optional[str] = None
    target_role: Optional[str] = None
    streak_count: int = Field(default=0)
    total_xp: int = Field(default=0)
    last_active_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SkillMaster(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    category: str

class UserSkill(SQLModel, table=True):
    user_id: str = Field(primary_key=True, foreign_key="user.id")
    skill_id: int = Field(primary_key=True, foreign_key="skillmaster.id")
    proficiency_level: int = Field(default=1) # 1: Beginner, 5: Expert
    is_target_skill: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Roadmap(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    title: str
    description: Optional[str] = None
    target_role: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class RoadmapNode(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    roadmap_id: str = Field(foreign_key="roadmap.id")
    parent_node_id: Optional[str] = Field(default=None, foreign_key="roadmapnode.id")
    title: str
    description: str
    difficulty: str = Field(default="BEGINNER") # BEGINNER, INTERMEDIATE, ADVANCED
    estimated_duration: str # e.g. "12 hours"
    resources: Optional[List[Dict[str, Any]]] = Field(default=None, sa_type=JSON) # [{title, url, type}]
    projects: Optional[List[Dict[str, Any]]] = Field(default=None, sa_type=JSON) # [{title, desc, tasks}]
    certifications: Optional[List[Dict[str, Any]]] = Field(default=None, sa_type=JSON) # [{name, provider}]
    status: str = Field(default="LOCKED") # LOCKED, AVAILABLE, IN_PROGRESS, COMPLETED
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Resume(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    title: str = Field(default="My Resume")
    ats_score: int = Field(default=0)
    theme: str = Field(default="classic")
    content: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    analysis_feedback: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserProjectProgress(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    roadmap_node_id: Optional[str] = Field(default=None, foreign_key="roadmapnode.id")
    project_title: str
    difficulty: str
    tech_stack: List[str] = Field(default_factory=list, sa_type=JSON)
    github_url: Optional[str] = None
    status: str = Field(default="NOT_STARTED") # NOT_STARTED, IN_PROGRESS, COMPLETED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class LearningSession(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    roadmap_node_id: Optional[str] = Field(default=None, foreign_key="roadmapnode.id")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    duration_minutes: int = Field(default=0)

class AIConversation(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    title: str = Field(default="New Conversation")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AIMessage(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    conversation_id: str = Field(foreign_key="aiconversation.id")
    sender: str = Field(index=True) # "user" or "assistant"
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
