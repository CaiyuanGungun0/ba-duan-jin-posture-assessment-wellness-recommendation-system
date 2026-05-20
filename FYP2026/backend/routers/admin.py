from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.auth import get_current_admin_user
from backend.database import get_db

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user_to_admin_out(user: models.User, db: Session) -> schemas.AdminUserOut:
    count = db.query(func.count(models.ExerciseSession.id)).filter(
        models.ExerciseSession.user_id == user.id
    ).scalar() or 0
    data = schemas.AdminUserOut.model_validate(user)
    data.session_count = count
    return data


# ── User Management ───────────────────────────────────────────────────────────

@router.get("/users", response_model=list[schemas.AdminUserOut])
def list_users(
    search: str | None = Query(None),
    role: str | None = Query(None),
    suspended: bool | None = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_current_admin_user),
):
    q = db.query(models.User)
    if search:
        like = f"%{search}%"
        q = q.filter(
            models.User.username.ilike(like) | models.User.email.ilike(like)
        )
    if role:
        q = q.filter(models.User.role == role)
    if suspended is not None:
        q = q.filter(models.User.is_suspended == suspended)
    users = q.order_by(models.User.created_at.desc()).offset(skip).limit(limit).all()
    return [_user_to_admin_out(u, db) for u in users]


@router.patch("/users/{user_id}", response_model=schemas.AdminUserOut)
def update_user(
    user_id: int,
    body: schemas.AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin_user),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own admin account here")
    if body.role is not None:
        user.role = body.role
    if body.is_suspended is not None:
        user.is_suspended = body.is_suspended
    db.commit()
    db.refresh(user)
    return _user_to_admin_out(user, db)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin_user),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    # cascade-delete related data
    for session in user.sessions:
        for action in session.session_actions:
            db.query(models.JointMetric).filter(
                models.JointMetric.session_action_id == action.id
            ).delete()
        db.query(models.SessionAction).filter(
            models.SessionAction.session_id == session.id
        ).delete()
        db.query(models.PoseScore).filter(
            models.PoseScore.session_id == session.id
        ).delete()
    db.query(models.ExerciseSession).filter(models.ExerciseSession.user_id == user_id).delete()
    db.query(models.DailyHealthLog).filter(models.DailyHealthLog.user_id == user_id).delete()
    db.query(models.FoodLog).filter(models.FoodLog.user_id == user_id).delete()
    db.query(models.WaterLog).filter(models.WaterLog.user_id == user_id).delete()
    db.query(models.Recommendation).filter(models.Recommendation.user_id == user_id).delete()
    db.query(models.UserAchievement).filter(models.UserAchievement.user_id == user_id).delete()
    db.query(models.Favorite).filter(models.Favorite.user_id == user_id).delete()
    db.query(models.SocialPost).filter(models.SocialPost.user_id == user_id).delete()
    db.query(models.Notification).filter(models.Notification.user_id == user_id).delete()
    db.query(models.AIHealthReport).filter(models.AIHealthReport.user_id == user_id).delete()
    db.query(models.HistoricalProgress).filter(models.HistoricalProgress.user_id == user_id).delete()
    db.query(models.Follower).filter(
        (models.Follower.follower_id == user_id) | (models.Follower.followee_id == user_id)
    ).delete()
    db.delete(user)
    db.commit()


# ── Session Monitoring ────────────────────────────────────────────────────────

@router.get("/sessions", response_model=list[schemas.AdminSessionOut])
def list_all_sessions(
    skip: int = 0,
    limit: int = 50,
    user_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_current_admin_user),
):
    q = db.query(models.ExerciseSession, models.User.username).join(
        models.User, models.ExerciseSession.user_id == models.User.id
    )
    if user_id:
        q = q.filter(models.ExerciseSession.user_id == user_id)
    rows = q.order_by(models.ExerciseSession.date.desc()).offset(skip).limit(limit).all()
    result = []
    for session, username in rows:
        result.append(schemas.AdminSessionOut(
            id=session.id,
            user_id=session.user_id,
            username=username,
            date=session.date,
            duration_seconds=session.duration_seconds,
            total_score=session.total_score,
            movement_count=session.movement_count,
            session_type=session.session_type,
            calories_burned=session.calories_burned,
            completed=session.completed,
        ))
    return result


@router.get("/sessions/{session_id}", response_model=schemas.AdminSessionDetail)
def get_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_current_admin_user),
):
    session = db.get(models.ExerciseSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    user = db.get(models.User, session.user_id)
    return schemas.AdminSessionDetail(
        id=session.id,
        user_id=session.user_id,
        username=user.username if user else "unknown",
        date=session.date,
        duration_seconds=session.duration_seconds,
        total_score=session.total_score,
        movement_count=session.movement_count,
        session_type=session.session_type,
        calories_burned=session.calories_burned,
        fatigue_score=session.fatigue_score,
        completed=session.completed,
        pose_scores=session.pose_scores,
        session_actions=session.session_actions,
    )


# ── Recommendation Rules ──────────────────────────────────────────────────────

@router.get("/recommendation-rules", response_model=list[schemas.RecommendationRuleOut])
def list_rules(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_current_admin_user),
):
    return db.query(models.RecommendationRule).order_by(
        models.RecommendationRule.priority.desc()
    ).all()


@router.post("/recommendation-rules", response_model=schemas.RecommendationRuleOut,
             status_code=status.HTTP_201_CREATED)
def create_rule(
    body: schemas.RecommendationRuleCreate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_current_admin_user),
):
    existing = db.query(models.RecommendationRule).filter(
        models.RecommendationRule.key == body.key
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Rule key already exists")
    rule = models.RecommendationRule(**body.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/recommendation-rules/{rule_id}", response_model=schemas.RecommendationRuleOut)
def update_rule(
    rule_id: int,
    body: schemas.RecommendationRuleUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_current_admin_user),
):
    rule = db.get(models.RecommendationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(rule, field, val)
    rule.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/recommendation-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_current_admin_user),
):
    rule = db.get(models.RecommendationRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()


# ── Dataset Oversight ─────────────────────────────────────────────────────────

@router.get("/dataset")
def dataset_overview(
    _admin: models.User = Depends(get_current_admin_user),
):
    data_dir = "data"
    samples = []
    if os.path.isdir(data_dir):
        for root, dirs, files in os.walk(data_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                fp = os.path.join(root, f)
                try:
                    size = os.path.getsize(fp)
                    mtime = datetime.fromtimestamp(os.path.getmtime(fp)).isoformat()
                except OSError:
                    size, mtime = 0, ""
                samples.append({
                    "path": fp.replace("\\", "/"),
                    "filename": f,
                    "size_bytes": size,
                    "modified_at": mtime,
                    "type": os.path.splitext(f)[1].lstrip(".") or "unknown",
                })
    return {
        "total_files": len(samples),
        "files": sorted(samples, key=lambda x: x["modified_at"], reverse=True)[:200],
    }


@router.get("/logs")
def system_logs(
    lines: int = Query(100, ge=10, le=500),
    _admin: models.User = Depends(get_current_admin_user),
):
    log_entries = []
    log_file = "app.log"
    if os.path.isfile(log_file):
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        for line in all_lines[-lines:]:
            log_entries.append(line.rstrip())
    else:
        log_entries = ["No log file found at app.log. Logging to stdout only."]
    return {"lines": log_entries, "log_file": log_file}


# ── Admin Reports ─────────────────────────────────────────────────────────────

@router.get("/stats", response_model=schemas.AdminUsageStats)
def usage_stats(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_current_admin_user),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    suspended_users = db.query(func.count(models.User.id)).filter(
        models.User.is_suspended == True
    ).scalar() or 0
    total_sessions = db.query(func.count(models.ExerciseSession.id)).scalar() or 0
    sessions_7d = db.query(func.count(models.ExerciseSession.id)).filter(
        models.ExerciseSession.date >= cutoff
    ).scalar() or 0
    avg_score = db.query(func.avg(models.ExerciseSession.total_score)).scalar() or 0.0
    active_users = db.query(func.count(func.distinct(models.ExerciseSession.user_id))).filter(
        models.ExerciseSession.date >= cutoff
    ).scalar() or 0
    total_recs = db.query(func.count(models.Recommendation.id)).scalar() or 0

    return schemas.AdminUsageStats(
        total_users=total_users,
        active_users_7d=active_users,
        total_sessions=total_sessions,
        sessions_7d=sessions_7d,
        avg_session_score=round(float(avg_score), 2),
        total_recommendations_generated=total_recs,
        suspended_users=suspended_users,
    )


@router.get("/accuracy", response_model=schemas.AdminAccuracyStats)
def accuracy_stats(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_current_admin_user),
):
    overall = db.query(func.avg(models.PoseScore.accuracy)).scalar() or 0.0

    movement_rows = (
        db.query(
            models.PoseScore.movement_name,
            func.avg(models.PoseScore.accuracy).label("avg_acc"),
            func.count(models.PoseScore.id).label("count"),
        )
        .group_by(models.PoseScore.movement_name)
        .order_by(func.avg(models.PoseScore.accuracy).asc())
        .all()
    )
    movement_accuracy = [
        {"movement": r.movement_name, "avg_accuracy": round(float(r.avg_acc), 2), "count": r.count}
        for r in movement_rows
    ]

    # 14-day trend
    trend = []
    for i in range(13, -1, -1):
        day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        avg = db.query(func.avg(models.PoseScore.accuracy)).filter(
            models.PoseScore.timestamp >= day_start,
            models.PoseScore.timestamp < day_end,
        ).scalar()
        trend.append({"date": day_start.strftime("%Y-%m-%d"), "avg_accuracy": round(float(avg or 0), 2)})

    return schemas.AdminAccuracyStats(
        overall_avg_accuracy=round(float(overall), 2),
        movement_accuracy=movement_accuracy,
        accuracy_trend=trend,
    )


@router.get("/model-eval")
def model_eval_logs(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_current_admin_user),
):
    # Aggregate session-level metrics as a proxy for model evaluation
    rows = (
        db.query(
            func.date(models.ExerciseSession.date).label("day"),
            func.count(models.ExerciseSession.id).label("sessions"),
            func.avg(models.ExerciseSession.total_score).label("avg_score"),
            func.avg(models.ExerciseSession.avg_fps).label("avg_fps"),
            func.avg(models.ExerciseSession.avg_latency_ms).label("avg_latency"),
        )
        .group_by(func.date(models.ExerciseSession.date))
        .order_by(func.date(models.ExerciseSession.date).desc())
        .limit(30)
        .all()
    )

    action_counts = (
        db.query(
            models.SessionAction.action_name,
            func.count(models.SessionAction.id).label("count"),
            func.avg(models.SessionAction.avg_score).label("avg_score"),
        )
        .group_by(models.SessionAction.action_name)
        .all()
    )

    return {
        "daily_metrics": [
            {
                "date": str(r.day),
                "sessions": r.sessions,
                "avg_score": round(float(r.avg_score or 0), 2),
                "avg_fps": round(float(r.avg_fps or 0), 2),
                "avg_latency_ms": round(float(r.avg_latency or 0), 2),
            }
            for r in rows
        ],
        "per_action_metrics": [
            {
                "action": r.action_name,
                "total_executions": r.count,
                "avg_score": round(float(r.avg_score or 0), 2),
            }
            for r in action_counts
        ],
    }
