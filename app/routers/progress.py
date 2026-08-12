from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/api", tags=["progress"])


@router.get("/progress", response_model=list[schemas.ProgressRead])
def list_progress(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(models.LabProgress).filter(
        models.LabProgress.user_id == current_user.id
    ).all()
    return rows


@router.put("/progress/{lab_id}", response_model=schemas.ProgressRead)
def upsert_progress(
    lab_id: str,
    payload: schemas.ProgressUpdate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(models.LabProgress).filter(
        models.LabProgress.user_id == current_user.id,
        models.LabProgress.lab_id == lab_id,
    ).first()

    if row is None:
        row = models.LabProgress(user_id=current_user.id, lab_id=lab_id)
        db.add(row)

    row.status = payload.status
    row.answered_task_ids = payload.answered_task_ids
    row.earned_points = payload.earned_points
    row.completed_at = payload.completed_at or (
        datetime.utcnow() if payload.status == "Completed" else row.completed_at
    )

    db.commit()
    db.refresh(row)
    return row


@router.get("/dashboard", response_model=schemas.DashboardStats)
def get_dashboard(
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    progress_rows = db.query(models.LabProgress).filter(
        models.LabProgress.user_id == current_user.id
    ).all()
    labs_completed = sum(1 for p in progress_rows if p.status == "Completed")
    labs_in_progress = sum(1 for p in progress_rows if p.status == "In Progress")
    total_points = sum(p.earned_points for p in progress_rows)

    submissions = db.query(models.QuizSubmission).filter(
        models.QuizSubmission.student_id == str(current_user.id)
    ).all()
    quizzes_taken = len(submissions)
    average_quiz_score = (
        sum(
            (s.score / s.total_points * 100) if s.total_points else 0
            for s in submissions
        )
        / quizzes_taken
        if quizzes_taken
        else 0.0
    )

    return schemas.DashboardStats(
        labs_completed=labs_completed,
        labs_in_progress=labs_in_progress,
        total_points=total_points,
        quizzes_taken=quizzes_taken,
        average_quiz_score=round(average_quiz_score, 1),
    )
