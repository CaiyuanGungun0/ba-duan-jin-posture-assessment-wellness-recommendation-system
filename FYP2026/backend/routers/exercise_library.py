from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.auth import get_current_user
from backend.database import get_db

router = APIRouter()


@router.get("/", response_model=list[schemas.ExerciseLibraryOut])
def list_exercises(
    category: str | None = Query(None),
    difficulty: str | None = Query(None),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    q = db.query(models.ExerciseLibrary)
    if category:
        q = q.filter(models.ExerciseLibrary.category == category)
    if difficulty:
        q = q.filter(models.ExerciseLibrary.difficulty == difficulty)
    return q.order_by(models.ExerciseLibrary.action_no.asc()).all()


@router.get("/{exercise_id}", response_model=schemas.ExerciseLibraryOut)
def get_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    from fastapi import HTTPException
    ex = db.get(models.ExerciseLibrary, exercise_id)
    if not ex:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return ex
