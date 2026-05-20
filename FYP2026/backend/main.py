from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import init_db
from backend.routers import (
    admin,
    auth,
    dashboard,
    exercise_library,
    gamification,
    notifications,
    pose,
    profile,
    recommendations,
    reports,
    sessions,
    social,
    wellness,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Ensure upload directories exist
    Path("uploads/avatars").mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Baduanjin Wellness Platform API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded avatars
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(admin.router,            prefix="/api/admin",            tags=["admin"])
app.include_router(auth.router,             prefix="/api/auth",             tags=["auth"])
app.include_router(profile.router,          prefix="/api/profile",          tags=["profile"])
app.include_router(sessions.router,         prefix="/api/sessions",         tags=["sessions"])
app.include_router(dashboard.router,        prefix="/api/dashboard",        tags=["dashboard"])
app.include_router(recommendations.router,  prefix="/api/recommendations",  tags=["recommendations"])
app.include_router(pose.router,             prefix="/api/pose",             tags=["pose"])
app.include_router(wellness.router,         prefix="/api/wellness",         tags=["wellness"])
app.include_router(gamification.router,     prefix="/api/gamification",     tags=["gamification"])
app.include_router(social.router,           prefix="/api/social",           tags=["social"])
app.include_router(notifications.router,    prefix="/api/notifications",    tags=["notifications"])
app.include_router(reports.router,          prefix="/api/reports",          tags=["reports"])
app.include_router(exercise_library.router, prefix="/api/exercises",        tags=["exercises"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Baduanjin Wellness Platform", "version": "2.0.0"}
