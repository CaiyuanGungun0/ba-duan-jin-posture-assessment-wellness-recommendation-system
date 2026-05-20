from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models, schemas


def update_daily_progress(db: Session, user_id: int) -> None:
    today = date.today()
    sessions_today = (
        db.query(models.ExerciseSession)
        .filter(
            models.ExerciseSession.user_id == user_id,
            func.date(models.ExerciseSession.date) == today,
        )
        .all()
    )
    if not sessions_today:
        return

    avg_score = sum(s.total_score for s in sessions_today) / len(sessions_today)
    existing = (
        db.query(models.HistoricalProgress)
        .filter(
            models.HistoricalProgress.user_id == user_id,
            func.date(models.HistoricalProgress.date) == today,
        )
        .first()
    )
    if existing:
        existing.avg_score = round(avg_score, 2)
        existing.sessions_count = len(sessions_today)
    else:
        db.add(models.HistoricalProgress(
            user_id=user_id,
            avg_score=round(avg_score, 2),
            sessions_count=len(sessions_today),
        ))
    db.commit()


def compute_dashboard(db: Session, user: models.User) -> schemas.DashboardSummary:
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    # ── Weekly stats ──────────────────────────────────────────────────────────
    recent_sessions = (
        db.query(models.ExerciseSession)
        .filter(
            models.ExerciseSession.user_id == user.id,
            models.ExerciseSession.date >= week_ago,
        )
        .all()
    )

    scores = [s.total_score for s in recent_sessions if s.total_score > 0]
    total_seconds = sum(s.duration_seconds for s in recent_sessions)
    calories_burned_week = sum(s.calories_burned for s in recent_sessions)

    progress_rows = (
        db.query(models.HistoricalProgress)
        .filter(models.HistoricalProgress.user_id == user.id)
        .order_by(models.HistoricalProgress.date.desc())
        .limit(30)
        .all()
    )
    streak = _compute_streak([r.date.date() for r in progress_rows])

    weekly_stats = schemas.WeeklyStats(
        sessions_this_week=len(recent_sessions),
        avg_accuracy=round(sum(scores) / len(scores), 1) if scores else 0.0,
        best_accuracy=round(max(scores), 1) if scores else 0.0,
        total_minutes=total_seconds // 60,
        streak_days=streak,
        total_points=user.total_points,
        level=user.level,
        calories_burned_week=round(calories_burned_week, 1),
    )

    # ── Progress history (last 14 days) ───────────────────────────────────────
    history = (
        db.query(models.HistoricalProgress)
        .filter(
            models.HistoricalProgress.user_id == user.id,
            models.HistoricalProgress.date >= now - timedelta(days=14),
        )
        .order_by(models.HistoricalProgress.date.asc())
        .all()
    )
    progress_history = [
        schemas.ProgressPoint(
            date=h.date.strftime("%Y-%m-%d"),
            avg_score=h.avg_score,
            sessions=h.sessions_count,
        )
        for h in history
    ]

    # ── Movement breakdown (last 30 days) ─────────────────────────────────────
    thirty_days_ago = now - timedelta(days=30)
    pose_scores = (
        db.query(models.PoseScore)
        .join(models.ExerciseSession)
        .filter(
            models.ExerciseSession.user_id == user.id,
            models.ExerciseSession.date >= thirty_days_ago,
        )
        .all()
    )

    movement_breakdown: list[schemas.MovementBreakdown] = []
    if pose_scores:
        df = pd.DataFrame([{"movement_name": p.movement_name, "accuracy": p.accuracy} for p in pose_scores])
        grouped = df.groupby("movement_name")["accuracy"].agg(["mean", "count"]).reset_index()
        movement_breakdown = [
            schemas.MovementBreakdown(
                movement_name=row["movement_name"],
                avg_accuracy=round(row["mean"], 1),
                count=int(row["count"]),
            )
            for _, row in grouped.iterrows()
        ]

    # ── Latest recommendation ─────────────────────────────────────────────────
    latest_rec = (
        db.query(models.Recommendation)
        .filter(models.Recommendation.user_id == user.id)
        .order_by(models.Recommendation.generated_at.desc())
        .first()
    )

    # ── Recent achievements ───────────────────────────────────────────────────
    recent_achievements = (
        db.query(models.UserAchievement)
        .filter(models.UserAchievement.user_id == user.id)
        .order_by(models.UserAchievement.earned_at.desc())
        .limit(3)
        .all()
    )
    achievements_data = []
    for ua in recent_achievements:
        a = db.get(models.Achievement, ua.achievement_id)
        if a:
            achievements_data.append({
                "title": a.title,
                "badge_icon": a.badge_icon,
                "points": a.points,
                "earned_at": ua.earned_at.isoformat(),
            })

    # ── Today's health log ────────────────────────────────────────────────────
    today_log = (
        db.query(models.DailyHealthLog)
        .filter(
            models.DailyHealthLog.user_id == user.id,
            func.date(models.DailyHealthLog.log_date) == date.today(),
        )
        .first()
    )
    today_health = None
    if today_log:
        today_health = {
            "water_ml": today_log.water_ml,
            "target_water_ml": user.target_water_ml,
            "sleep_hours": today_log.sleep_hours,
            "mood": today_log.mood,
            "stress_level": today_log.stress_level,
            "steps": today_log.steps,
        }

    return schemas.DashboardSummary(
        weekly_stats=weekly_stats,
        progress_history=progress_history,
        movement_breakdown=movement_breakdown,
        latest_recommendation=latest_rec.content if latest_rec else None,
        recent_achievements=achievements_data,
        today_health=today_health,
    )


def _compute_streak(session_dates: list[date]) -> int:
    if not session_dates:
        return 0
    unique = sorted(set(session_dates), reverse=True)
    streak = 0
    expected = date.today()
    for d in unique:
        if d == expected or d == expected - timedelta(days=1):
            streak += 1
            expected = d - timedelta(days=1)
        else:
            break
    return streak


def build_user_context(db: Session, user: models.User) -> dict:
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent = (
        db.query(models.ExerciseSession)
        .filter(
            models.ExerciseSession.user_id == user.id,
            models.ExerciseSession.date >= week_ago,
        )
        .all()
    )

    pose_scores = (
        db.query(models.PoseScore)
        .join(models.ExerciseSession)
        .filter(
            models.ExerciseSession.user_id == user.id,
            models.ExerciseSession.date >= week_ago,
        )
        .all()
    )

    avg_accuracy = 0.0
    movement_issues: list[str] = []
    if pose_scores:
        df = pd.DataFrame([{"name": p.movement_name, "acc": p.accuracy} for p in pose_scores])
        avg_accuracy = round(df["acc"].mean(), 1)
        low = df[df["acc"] < 65].groupby("name")["acc"].mean()
        movement_issues = [f"{name} ({round(acc, 0):.0f}%)" for name, acc in low.items()]

    total_min = sum(s.duration_seconds for s in recent) // 60

    return {
        "username": user.username,
        "age": user.age,
        "sessions_this_week": len(recent),
        "avg_accuracy_pct": avg_accuracy,
        "total_practice_minutes": total_min,
        "low_accuracy_movements": movement_issues,
        "stress_level": user.stress_level,
        "sleep_quality": user.sleep_quality,
        "target_goal": user.target_goal,
        "streak_days": user.streak_days,
    }
