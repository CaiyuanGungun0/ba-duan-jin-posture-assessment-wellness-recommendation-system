from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.auth import get_current_user
from backend.database import get_db
from backend.services.gamification_service import check_and_award_achievements

router = APIRouter()


@router.get("/achievements", response_model=list[schemas.AchievementOut])
def list_all_achievements(db: Session = Depends(get_db)):
    return db.query(models.Achievement).all()


@router.get("/my-achievements", response_model=list[schemas.UserAchievementOut])
def my_achievements(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.UserAchievement)
        .filter(models.UserAchievement.user_id == current_user.id)
        .order_by(models.UserAchievement.earned_at.desc())
        .all()
    )


@router.post("/check-achievements", response_model=list[schemas.AchievementOut])
def trigger_achievement_check(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    newly_earned = check_and_award_achievements(db, current_user)
    return newly_earned


@router.get("/leaderboard", response_model=list[schemas.LeaderboardEntry])
def leaderboard(
    limit: int = 20,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    users = (
        db.query(models.User)
        .filter(models.User.is_public_profile == True)
        .order_by(models.User.total_points.desc())
        .limit(limit)
        .all()
    )
    return [
        schemas.LeaderboardEntry(
            rank=i + 1,
            user_id=u.id,
            username=u.username,
            profile_photo=u.profile_photo,
            total_points=u.total_points,
            level=u.level,
            streak_days=u.streak_days,
        )
        for i, u in enumerate(users)
    ]


@router.get("/my-rank", response_model=dict)
def my_rank(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rank = (
        db.query(models.User)
        .filter(
            models.User.is_public_profile == True,
            models.User.total_points > current_user.total_points,
        )
        .count()
        + 1
    )
    return {
        "rank": rank,
        "total_points": current_user.total_points,
        "level": current_user.level,
        "streak_days": current_user.streak_days,
        "next_level_points": _next_level_points(current_user.total_points),
    }


def _next_level_points(points: int) -> int:
    thresholds = [500, 1500, 3000]
    for t in thresholds:
        if points < t:
            return t
    return points  # already Platinum
