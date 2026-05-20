from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.auth import get_current_user
from backend.database import get_db

router = APIRouter()


@router.get("/", response_model=list[schemas.NotificationOut])
def list_notifications(
    limit: int = 30,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id
    )
    if unread_only:
        q = q.filter(models.Notification.read_flag == False)
    return q.order_by(models.Notification.created_at.desc()).limit(limit).all()


@router.post("/{notif_id}/read", response_model=schemas.NotificationOut)
def mark_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    notif = db.get(models.Notification, notif_id)
    if not notif or notif.user_id != current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.read_flag = True
    db.commit()
    db.refresh(notif)
    return notif


@router.post("/read-all", response_model=dict)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.read_flag == False,
    ).update({"read_flag": True})
    db.commit()
    return {"message": "All notifications marked as read"}


@router.get("/unread-count", response_model=dict)
def unread_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    count = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.read_flag == False,
    ).count()
    return {"unread_count": count}
