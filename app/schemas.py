from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "Student"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    university: Optional[str] = None
    study_plan: Optional[str] = None
    major: Optional[str] = None
    github_connected: bool = False
    github_username: Optional[str] = None
    onboarding_completed: bool = False
    picture: Optional[str] = None
    provider: Optional[str] = None

    class Config:
        from_attributes = True  # pydantic v2 (use orm_mode = True on pydantic v1)


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    university: Optional[str] = None
    study_plan: Optional[str] = None
    major: Optional[str] = None
    github_connected: Optional[bool] = None
    github_username: Optional[str] = None
    onboarding_completed: Optional[bool] = None
    picture: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


# ── Lab progress ─────────────────────────────────────────────────────────────

class ProgressUpdate(BaseModel):
    status: str  # "Not Started" | "In Progress" | "Completed"
    answered_task_ids: List[str] = []
    earned_points: int = 0
    completed_at: Optional[datetime] = None


class ProgressRead(BaseModel):
    lab_id: str
    status: str
    answered_task_ids: List[str]
    earned_points: int
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    labs_completed: int
    labs_in_progress: int
    total_points: int
    quizzes_taken: int
    average_quiz_score: float


# ── Quizzes ──────────────────────────────────────────────────────────────────

class QuizQuestion(BaseModel):
    id: str
    text: str
    type: str  # "mcq" | "truefalse"
    options: List[str]
    correctAnswer: int
    points: int


class QuizCreate(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    published: bool = False
    time_limit: Optional[int] = None
    questions: List[QuizQuestion] = []


class QuizRead(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    created_by: str
    created_at: datetime
    published: bool
    time_limit: Optional[int] = None
    questions: List[QuizQuestion]

    class Config:
        from_attributes = True


class SubmissionCreate(BaseModel):
    answers: List[Optional[int]]
    time_spent_seconds: int = 0


class SubmissionRead(BaseModel):
    id: str
    quiz_id: str
    student_id: str
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    answers: List[Optional[int]]
    submitted_at: datetime
    score: int
    total_points: int
    time_spent_seconds: int
    ai_detection_score: int

    class Config:
        from_attributes = True


# ── AI mentor (basic, rule-based — see routers/mentor.py) ────────────────────

class MentorAsk(BaseModel):
    question: str


class MentorReply(BaseModel):
    answer: str
