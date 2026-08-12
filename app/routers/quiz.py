import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])


@router.get("", response_model=list[schemas.QuizRead])
def list_quizzes(
    published_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    query = db.query(models.Quiz)
    if published_only:
        query = query.filter(models.Quiz.published == True)  # noqa: E712
    return query.all()


@router.post("", response_model=schemas.QuizRead, status_code=status.HTTP_201_CREATED)
def create_or_update_quiz(
    payload: schemas.QuizCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "Instructor":
        raise HTTPException(status_code=403, detail="Only instructors can create quizzes.")

    quiz = db.query(models.Quiz).filter(models.Quiz.id == payload.id).first()
    questions_json = [q.model_dump() for q in payload.questions]

    if quiz is None:
        quiz = models.Quiz(id=payload.id, created_by=current_user.email)
        db.add(quiz)

    quiz.title = payload.title
    quiz.description = payload.description
    quiz.published = payload.published
    quiz.time_limit = payload.time_limit
    quiz.questions = questions_json

    db.commit()
    db.refresh(quiz)
    return quiz


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quiz(
    quiz_id: str,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if quiz:
        db.query(models.QuizSubmission).filter(
            models.QuizSubmission.quiz_id == quiz_id
        ).delete()
        db.delete(quiz)
        db.commit()


@router.post("/{quiz_id}/submit", response_model=schemas.SubmissionRead)
def submit_quiz(
    quiz_id: str,
    payload: schemas.SubmissionCreate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    questions = quiz.questions or []
    total_points = sum(q.get("points", 0) for q in questions)
    score = 0
    for i, q in enumerate(questions):
        given = payload.answers[i] if i < len(payload.answers) else None
        if given is not None and given == q.get("correctAnswer"):
            score += q.get("points", 0)

    # Replace any previous submission by this student for this quiz.
    existing = db.query(models.QuizSubmission).filter(
        models.QuizSubmission.quiz_id == quiz_id,
        models.QuizSubmission.student_id == str(current_user.id),
    ).first()
    if existing:
        db.delete(existing)
        db.commit()

    submission = models.QuizSubmission(
        id=str(uuid.uuid4()),
        quiz_id=quiz_id,
        student_id=str(current_user.id),
        student_name=current_user.name,
        student_email=current_user.email,
        answers=payload.answers,
        score=score,
        total_points=total_points,
        time_spent_seconds=payload.time_spent_seconds,
        ai_detection_score=0,  # heuristic detection can be added later
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/{quiz_id}/submissions", response_model=list[schemas.SubmissionRead])
def list_submissions(
    quiz_id: str,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "Instructor":
        raise HTTPException(status_code=403, detail="Only instructors can view all submissions.")
    return db.query(models.QuizSubmission).filter(
        models.QuizSubmission.quiz_id == quiz_id
    ).all()


@router.get("/{quiz_id}/my-submission", response_model=Optional[schemas.SubmissionRead])
def my_submission(
    quiz_id: str,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(models.QuizSubmission).filter(
        models.QuizSubmission.quiz_id == quiz_id,
        models.QuizSubmission.student_id == str(current_user.id),
    ).first()
