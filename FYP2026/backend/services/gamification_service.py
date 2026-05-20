from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from backend import models


LEVEL_THRESHOLDS = [
    (0, "Bronze"),
    (500, "Silver"),
    (1500, "Gold"),
    (3000, "Platinum"),
]


def compute_level(points: int) -> str:
    level = "Bronze"
    for threshold, name in LEVEL_THRESHOLDS:
        if points >= threshold:
            level = name
    return level


def award_points(db: Session, user: models.User, points: int, reason: str = "") -> None:
    user.total_points += points
    user.level = compute_level(user.total_points)
    db.commit()

    # Create notification for point award
    notif = models.Notification(
        user_id=user.id,
        type="points",
        content=f"You earned {points} points! {reason}",
    )
    db.add(notif)
    db.commit()


def check_and_award_achievements(db: Session, user: models.User) -> list[models.Achievement]:
    all_achievements = db.query(models.Achievement).all()
    earned_ids = {ua.achievement_id for ua in db.query(models.UserAchievement).filter(
        models.UserAchievement.user_id == user.id
    ).all()}

    newly_earned: list[models.Achievement] = []

    # Compute current stats
    total_sessions = db.query(models.ExerciseSession).filter(
        models.ExerciseSession.user_id == user.id
    ).count()

    total_reps = db.query(models.SessionAction).join(models.ExerciseSession).filter(
        models.ExerciseSession.user_id == user.id
    ).with_entities(models.SessionAction.rep_count).all()
    total_reps_count = sum(r[0] for r in total_reps)

    scores = db.query(models.ExerciseSession).filter(
        models.ExerciseSession.user_id == user.id
    ).with_entities(models.ExerciseSession.total_score).all()
    avg_score = sum(r[0] for r in scores) / max(1, len(scores))

    water_days = db.query(models.DailyHealthLog).filter(
        models.DailyHealthLog.user_id == user.id,
        models.DailyHealthLog.water_ml >= 2000,
    ).count()

    stat_map = {
        "streak_days": user.streak_days,
        "total_sessions": total_sessions,
        "total_reps": total_reps_count,
        "avg_score": avg_score,
        "water_days": water_days,
        "total_points": user.total_points,
    }

    for achievement in all_achievements:
        if achievement.id in earned_ids:
            continue

        current_val = stat_map.get(achievement.condition_type, 0)
        if current_val >= achievement.condition_value:
            ua = models.UserAchievement(
                user_id=user.id,
                achievement_id=achievement.id,
                earned_at=datetime.utcnow(),
            )
            db.add(ua)
            award_points(db, user, achievement.points, f"for '{achievement.title}'")
            newly_earned.append(achievement)

            notif = models.Notification(
                user_id=user.id,
                type="achievement",
                content=f"You earned the '{achievement.title}' badge! {achievement.badge_icon}",
            )
            db.add(notif)

    if newly_earned:
        db.commit()

    return newly_earned


def update_streak(db: Session, user: models.User) -> None:
    today = datetime.utcnow().date()
    last_active = user.last_active_date.date() if user.last_active_date else None

    if last_active is None or (today - last_active).days > 1:
        user.streak_days = 1
    elif (today - last_active).days == 1:
        user.streak_days += 1
    # same day = no change

    user.last_active_date = datetime.utcnow()
    db.commit()
