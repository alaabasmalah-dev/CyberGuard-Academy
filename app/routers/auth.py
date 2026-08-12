from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists. Please sign in instead.",
        )

    user = models.User(
        name=payload.name,
        email=payload.email.lower(),
        hashed_password=security.hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = security.create_access_token({"sub": str(user.id)})
    return schemas.Token(access_token=token, user=schemas.UserRead.model_validate(user))


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No account found. Please create an account first.",
        )
    if not security.verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password.",
        )

    token = security.create_access_token({"sub": str(user.id)})
    return schemas.Token(access_token=token, user=schemas.UserRead.model_validate(user))


@router.get("/me", response_model=schemas.UserRead)
def read_current_user(current_user: models.User = Depends(security.get_current_user)):
    return current_user


@router.patch("/me", response_model=schemas.UserRead)
def update_current_user(
    updates: schemas.UserUpdate,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/logout")
def logout():
    # JWT tokens are stateless — there's nothing to invalidate server-side.
    # The frontend simply deletes the stored token. This endpoint exists so
    # the existing frontend call to POST /api/auth/logout keeps working.
    return {"success": True}
