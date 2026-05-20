from __future__ import annotations

from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.auth import get_current_user
from backend.database import get_db

router = APIRouter()


# ── Daily Health Log ──────────────────────────────────────────────────────────

@router.post("/health-log", response_model=schemas.DailyHealthLogOut, status_code=201)
def upsert_health_log(
    body: schemas.DailyHealthLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    log_day = body.log_date.date()
    existing = (
        db.query(models.DailyHealthLog)
        .filter(
            models.DailyHealthLog.user_id == current_user.id,
            func.date(models.DailyHealthLog.log_date) == log_day,
        )
        .first()
    )

    if existing:
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing

    log = models.DailyHealthLog(user_id=current_user.id, **body.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/health-log", response_model=list[schemas.DailyHealthLogOut])
def list_health_logs(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(models.DailyHealthLog)
        .filter(
            models.DailyHealthLog.user_id == current_user.id,
            models.DailyHealthLog.log_date >= since,
        )
        .order_by(models.DailyHealthLog.log_date.desc())
        .all()
    )


@router.get("/health-log/today", response_model=schemas.DailyHealthLogOut | None)
def get_today_health_log(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    today = datetime.utcnow().date()
    return (
        db.query(models.DailyHealthLog)
        .filter(
            models.DailyHealthLog.user_id == current_user.id,
            func.date(models.DailyHealthLog.log_date) == today,
        )
        .first()
    )


# ── Food Log ──────────────────────────────────────────────────────────────────

@router.post("/food-log", response_model=schemas.FoodLogOut, status_code=201)
def add_food_log(
    body: schemas.FoodLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    log = models.FoodLog(user_id=current_user.id, **body.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/food-log", response_model=list[schemas.FoodLogOut])
def list_food_logs(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(models.FoodLog)
        .filter(
            models.FoodLog.user_id == current_user.id,
            models.FoodLog.timestamp >= since,
        )
        .order_by(models.FoodLog.timestamp.desc())
        .all()
    )


@router.delete("/food-log/{log_id}", status_code=204)
def delete_food_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    log = db.get(models.FoodLog, log_id)
    if not log or log.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Log not found")
    db.delete(log)
    db.commit()


# ── Water Log ─────────────────────────────────────────────────────────────────

@router.post("/water-log", response_model=schemas.WaterLogOut, status_code=201)
def add_water_log(
    body: schemas.WaterLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    log = models.WaterLog(user_id=current_user.id, amount_ml=body.amount_ml)
    db.add(log)
    db.commit()
    db.refresh(log)

    # Update daily health log water total
    today = datetime.utcnow().date()
    daily = (
        db.query(models.DailyHealthLog)
        .filter(
            models.DailyHealthLog.user_id == current_user.id,
            func.date(models.DailyHealthLog.log_date) == today,
        )
        .first()
    )
    if daily:
        daily.water_ml = (daily.water_ml or 0) + body.amount_ml
        db.commit()

    return log


@router.get("/water-log/today", response_model=dict)
def get_today_water(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    today = datetime.utcnow().date()
    since = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    logs = (
        db.query(models.WaterLog)
        .filter(
            models.WaterLog.user_id == current_user.id,
            models.WaterLog.timestamp >= since,
        )
        .all()
    )
    total = sum(l.amount_ml for l in logs)
    return {
        "total_ml": total,
        "target_ml": current_user.target_water_ml,
        "pct": round(min(100, total / max(1, current_user.target_water_ml) * 100), 1),
        "logs": [{"id": l.id, "amount_ml": l.amount_ml, "timestamp": l.timestamp} for l in logs],
    }


# ── Wellness Summary ──────────────────────────────────────────────────────────

@router.get("/summary", response_model=dict)
def wellness_summary(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(days=days)
    logs = (
        db.query(models.DailyHealthLog)
        .filter(
            models.DailyHealthLog.user_id == current_user.id,
            models.DailyHealthLog.log_date >= since,
        )
        .all()
    )

    if not logs:
        return {"message": "No health logs yet", "logs": []}

    avg_sleep = (
        sum(l.sleep_hours for l in logs if l.sleep_hours) /
        max(1, sum(1 for l in logs if l.sleep_hours))
    )
    avg_stress = (
        sum(l.stress_level for l in logs if l.stress_level) /
        max(1, sum(1 for l in logs if l.stress_level))
    )
    mood_counts: dict[str, int] = {}
    for l in logs:
        if l.mood:
            mood_counts[l.mood] = mood_counts.get(l.mood, 0) + 1

    return {
        "avg_sleep_hours": round(avg_sleep, 1),
        "avg_stress_level": round(avg_stress, 1),
        "mood_distribution": mood_counts,
        "total_water_ml": sum(l.water_ml for l in logs),
        "avg_steps": round(sum(l.steps for l in logs) / max(1, len(logs))),
        "days_logged": len(logs),
        "logs": [schemas.DailyHealthLogOut.model_validate(l).model_dump() for l in logs],
    }
