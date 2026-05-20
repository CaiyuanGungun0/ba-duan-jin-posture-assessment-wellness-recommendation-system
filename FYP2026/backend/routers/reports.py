from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.auth import get_current_user
from backend.database import get_db

router = APIRouter()


@router.get("/", response_model=list[schemas.AIHealthReportOut])
def list_reports(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.AIHealthReport)
        .filter(models.AIHealthReport.user_id == current_user.id)
        .order_by(models.AIHealthReport.generated_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/generate", response_model=schemas.AIHealthReportOut)
def generate_report(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(days=7)

    sessions = db.query(models.ExerciseSession).filter(
        models.ExerciseSession.user_id == current_user.id,
        models.ExerciseSession.date >= since,
    ).all()

    scores = [s.total_score for s in sessions]
    avg_score = round(sum(scores) / max(1, len(scores)), 1)

    health_logs = db.query(models.DailyHealthLog).filter(
        models.DailyHealthLog.user_id == current_user.id,
        models.DailyHealthLog.log_date >= since,
    ).all()

    avg_sleep = (
        round(sum(l.sleep_hours for l in health_logs if l.sleep_hours) /
              max(1, sum(1 for l in health_logs if l.sleep_hours)), 1)
        if health_logs else None
    )
    avg_stress = (
        round(sum(l.stress_level for l in health_logs if l.stress_level) /
              max(1, sum(1 for l in health_logs if l.stress_level)), 1)
        if health_logs else None
    )

    # Determine posture trend
    if len(scores) >= 2:
        first_half = scores[:len(scores)//2]
        second_half = scores[len(scores)//2:]
        trend_diff = (sum(second_half)/len(second_half)) - (sum(first_half)/len(first_half))
        posture_trend = "improving" if trend_diff > 2 else ("declining" if trend_diff < -2 else "stable")
    else:
        posture_trend = "stable"

    # Risk score (simple heuristic)
    risk_score = 0.0
    if avg_sleep and avg_sleep < 6:
        risk_score += 2.0
    if avg_stress and avg_stress > 7:
        risk_score += 2.0
    if avg_score < 60:
        risk_score += 3.0
    elif avg_score < 75:
        risk_score += 1.0
    if current_user.streak_days == 0:
        risk_score += 1.0
    risk_score = min(10.0, risk_score)

    # Generate text summary
    recs = []
    if avg_score < 70:
        recs.append("Focus on maintaining proper joint alignment during exercises.")
    if avg_sleep and avg_sleep < 7:
        recs.append(f"Your average sleep of {avg_sleep}h is below optimal. Aim for 7-9 hours.")
    if avg_stress and avg_stress > 6:
        recs.append("High stress detected. Try the breathing exercises before your sessions.")
    if current_user.streak_days >= 3:
        recs.append(f"Excellent {current_user.streak_days}-day streak! Consistency is key to improvement.")
    if not recs:
        recs.append("Your health metrics look great this week. Keep up the excellent work!")

    summary = (
        f"Weekly Health Report — {datetime.utcnow().strftime('%Y-%m-%d')}\n"
        f"Sessions completed: {len(sessions)} | Avg posture score: {avg_score}%\n"
        f"Sleep: {avg_sleep or 'N/A'}h | Stress level: {avg_stress or 'N/A'}/10\n"
        f"Posture trend: {posture_trend.title()}"
    )

    report = models.AIHealthReport(
        user_id=current_user.id,
        posture_trend=posture_trend,
        risk_score=round(risk_score, 1),
        recommendation="\n".join(f"• {r}" for r in recs),
        summary=summary,
        generated_at=datetime.utcnow(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    notif = models.Notification(
        user_id=current_user.id,
        type="report",
        content="Your weekly health report is ready. Check it out!",
    )
    db.add(notif)
    db.commit()

    return report
