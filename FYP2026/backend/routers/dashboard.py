from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.auth import get_current_user
from backend.database import get_db
from backend.services.analytics import compute_dashboard

router = APIRouter()


@router.get("/", response_model=schemas.DashboardSummary)
def dashboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return compute_dashboard(db, current_user)
