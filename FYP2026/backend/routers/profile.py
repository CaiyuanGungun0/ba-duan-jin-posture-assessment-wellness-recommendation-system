from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.auth import get_current_user, hash_password, verify_password
from backend.database import get_db

router = APIRouter()

UPLOAD_DIR = Path("uploads/avatars")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/", response_model=schemas.UserProfile)
def get_profile(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.patch("/", response_model=schemas.UserProfile)
def update_profile(
    body: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    update_data = body.model_dump(exclude_none=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    # Auto-compute BMI when height and weight are both known
    h = current_user.height_cm
    w = current_user.weight_kg
    if h and w and h > 0:
        current_user.bmi = round(w / ((h / 100) ** 2), 1)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/avatar", response_model=schemas.UserProfile)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Only JPEG/PNG/WebP images are allowed")

    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    save_path = UPLOAD_DIR / filename

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be under 5 MB")

    with open(save_path, "wb") as f:
        f.write(content)

    current_user.profile_photo = f"/uploads/avatars/{filename}"
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: schemas.PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = hash_password(body.new_password)
    db.commit()


@router.get("/stats", response_model=dict)
def get_my_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    total_sessions = db.query(models.ExerciseSession).filter(
        models.ExerciseSession.user_id == current_user.id
    ).count()

    total_minutes = db.query(models.ExerciseSession).filter(
        models.ExerciseSession.user_id == current_user.id
    ).with_entities(models.ExerciseSession.duration_seconds).all()
    total_minutes_val = sum(r[0] for r in total_minutes) // 60 if total_minutes else 0

    achievements_count = db.query(models.UserAchievement).filter(
        models.UserAchievement.user_id == current_user.id
    ).count()

    followers_count = db.query(models.Follower).filter(
        models.Follower.followee_id == current_user.id
    ).count()

    following_count = db.query(models.Follower).filter(
        models.Follower.follower_id == current_user.id
    ).count()

    return {
        "total_sessions": total_sessions,
        "total_minutes": total_minutes_val,
        "total_points": current_user.total_points,
        "level": current_user.level,
        "streak_days": current_user.streak_days,
        "achievements_count": achievements_count,
        "followers_count": followers_count,
        "following_count": following_count,
    }
