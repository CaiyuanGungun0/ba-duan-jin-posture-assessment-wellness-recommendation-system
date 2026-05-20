from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.auth import get_current_user
from backend.database import get_db
from backend.services.llm_service import generate_recommendation

router = APIRouter()


@router.post("/generate", response_model=schemas.RecommendationOut)
def generate(
    body: schemas.GenerateRecommendationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not body.force_refresh:
        # Return today's recommendation if it exists
        from datetime import date
        from sqlalchemy import func, cast, Date
        today_rec = (
            db.query(models.Recommendation)
            .filter(
                models.Recommendation.user_id == current_user.id,
                cast(models.Recommendation.generated_at, Date) == date.today(),
            )
            .order_by(models.Recommendation.generated_at.desc())
            .first()
        )
        if today_rec:
            return today_rec

    content = generate_recommendation(db, current_user)
    rec = models.Recommendation(user_id=current_user.id, content=content)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


@router.get("/", response_model=list[schemas.RecommendationOut])
def list_recommendations(
    limit: int = 7,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Recommendation)
        .filter(models.Recommendation.user_id == current_user.id)
        .order_by(models.Recommendation.generated_at.desc())
        .limit(limit)
        .all()
    )
