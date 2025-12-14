"""
Database models using SQLModel.
"""
from datetime import datetime, date
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum


class SessionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    RESCHEDULED = "rescheduled"


class Priority(int, Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


# ============ User Model ============
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    email: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============ Study Plan Model ============
class StudyPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str
    goal: Optional[str] = None
    start_date: date
    end_date: date
    hours_per_day: float = Field(default=4.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)


# ============ Subject Model ============
class Subject(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="studyplan.id", index=True)
    name: str = Field(index=True)
    description: Optional[str] = None


# ============ Topic Model ============
class Topic(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subject_id: int = Field(foreign_key="subject.id", index=True)
    name: str
    difficulty: int = Field(default=2, ge=1, le=3)
    estimated_hours: float = Field(default=1.0)


# ============ Study Session Model ============
class StudySession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="studyplan.id", index=True)
    topic_id: Optional[int] = Field(default=None, foreign_key="topic.id", index=True)
    subject_name: str = Field(default="")
    topic_name: str = Field(default="")
    scheduled_date: date
    scheduled_time: str = Field(default="09:00")
    duration_hours: float = Field(default=1.0)
    duration_minutes: int = Field(default=60)
    status: SessionStatus = Field(default=SessionStatus.PENDING)
    priority: Priority = Field(default=Priority.MEDIUM)
    notes: Optional[str] = None
    actual_duration: Optional[float] = None
    completed_at: Optional[datetime] = None
    original_date: Optional[date] = None


# ============ Knowledge Document Model ============
class KnowledgeDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    filename: str
    subject: Optional[str] = None
    file_path: str
    chunk_count: int = Field(default=0)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


# ============ Chat Message Model ============
class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: str  # "user" or "assistant"
    content: str
    agent_type: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
