from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.auth import get_current_user
from backend.database import get_db
from backend.services.analytics import update_daily_progress
from backend.services.gamification_service import (
    award_points,
    check_and_award_achievements,
    update_streak,
)

router = APIRouter()

POINTS_PER_SESSION = 20
POINTS_BONUS_HIGH_SCORE = 15   # score >= 85
POINTS_BONUS_ALL_ACTIONS = 10  # all 8 actions completed


@router.post("/", response_model=schemas.SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    body: schemas.SessionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    scores = body.pose_scores
    total_score = round(sum(s.accuracy for s in scores) / len(scores), 2) if scores else 0.0

    session = models.ExerciseSession(
        user_id=current_user.id,
        duration_seconds=body.duration_seconds,
        total_score=total_score,
        movement_count=len(scores),
        notes=body.notes,
        session_type=body.session_type,
        calories_burned=body.calories_burned,
        fatigue_score=body.fatigue_score,
    )
    db.add(session)
    db.flush()

    for ps in scores:
        db.add(models.PoseScore(
            session_id=session.id,
            movement_name=ps.movement_name,
            accuracy=ps.accuracy,
        ))

    for sa in body.session_actions:
        action = models.SessionAction(
            session_id=session.id,
            action_no=sa.action_no,
            action_name=sa.action_name,
            rep_count=sa.rep_count,
            avg_score=sa.avg_score,
            max_score=sa.max_score,
            advice_summary=sa.advice_summary,
            fatigue_score=sa.fatigue_score,
            completion_pct=sa.completion_pct,
        )
        db.add(action)

    db.commit()
    db.refresh(session)
    update_daily_progress(db, current_user.id)
    update_streak(db, current_user)

    # Award points
    pts = POINTS_PER_SESSION
    if total_score >= 85:
        pts += POINTS_BONUS_HIGH_SCORE
    if len(scores) >= 8:
        pts += POINTS_BONUS_ALL_ACTIONS
    award_points(db, current_user, pts, "for completing a session")
    check_and_award_achievements(db, current_user)

    db.refresh(session)
    return session


@router.get("/", response_model=list[schemas.SessionOut])
def list_sessions(
    limit: int = 20,
    session_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.ExerciseSession).filter(
        models.ExerciseSession.user_id == current_user.id
    )
    if session_type:
        q = q.filter(models.ExerciseSession.session_type == session_type)
    return q.order_by(models.ExerciseSession.date.desc()).limit(limit).all()


@router.get("/{session_id}", response_model=schemas.SessionOut)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = db.get(models.ExerciseSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = db.get(models.ExerciseSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    for action in session.session_actions:
        db.query(models.JointMetric).filter(
            models.JointMetric.session_action_id == action.id
        ).delete()
    db.query(models.SessionAction).filter(
        models.SessionAction.session_id == session_id
    ).delete()
    db.query(models.PoseScore).filter(
        models.PoseScore.session_id == session_id
    ).delete()
    db.delete(session)
    db.commit()


@router.get("/{session_id}/actions", response_model=list[schemas.SessionActionOut])
def get_session_actions(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = db.get(models.ExerciseSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return (
        db.query(models.SessionAction)
        .filter(models.SessionAction.session_id == session_id)
        .order_by(models.SessionAction.action_no)
        .all()
    )
