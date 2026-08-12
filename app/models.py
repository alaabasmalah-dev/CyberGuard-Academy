from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=True)  # nullable for future OAuth users
    role = Column(String(16), default="Student")  # "Student" | "Instructor"

    university = Column(String(128), nullable=True)
    study_plan = Column(String(128), nullable=True)
    major = Column(String(128), nullable=True)

    github_connected = Column(Boolean, default=False)
    github_username = Column(String(128), nullable=True)

    onboarding_completed = Column(Boolean, default=False)

    picture = Column(String(512), nullable=True)
    provider = Column(String(32), nullable=True)  # "google" | None


class LabProgress(Base):
    """One row per (user, lab) — tracks a student's progress through a lab."""
    __tablename__ = "lab_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    lab_id = Column(String(64), index=True, nullable=False)

    status = Column(String(32), default="Not Started")  # Not Started | In Progress | Completed
    answered_task_ids = Column(JSON, default=list)
    earned_points = Column(Integer, default=0)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Quiz(Base):
    """Instructor-authored quiz. Questions are stored as JSON — same shape the
    frontend already uses, so no extra normalization needed."""
    __tablename__ = "quizzes"

    id = Column(String(64), primary_key=True)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(String(128), nullable=False)  # instructor email
    created_at = Column(DateTime, server_default=func.now())
    published = Column(Boolean, default=False)
    time_limit = Column(Integer, nullable=True)  # minutes, null = no limit
    questions = Column(JSON, default=list)


class QuizSubmission(Base):
    __tablename__ = "quiz_submissions"

    id = Column(String(64), primary_key=True)
    quiz_id = Column(String(64), index=True, nullable=False)
    student_id = Column(String(64), index=True, nullable=False)
    student_name = Column(String(128), nullable=True)
    student_email = Column(String(128), nullable=True)
    answers = Column(JSON, default=list)
    submitted_at = Column(DateTime, server_default=func.now())
    score = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    time_spent_seconds = Column(Integer, default=0)
    ai_detection_score = Column(Integer, default=0)
