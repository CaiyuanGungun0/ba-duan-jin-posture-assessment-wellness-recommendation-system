from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


# ── Core User ──────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(String(20), default="user")  # user | admin

    # Basic demographics
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    bmi: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Self-report health
    stress_level: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 1-5
    sleep_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5

    # Fitness profile
    target_goal: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # lose_weight | maintain_health | improve_flexibility | improve_posture | stress_relief
    activity_level: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # sedentary | light | moderate | active | very_active
    health_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON array string
    exercise_preferences: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON

    # Daily targets
    target_exercise_minutes: Mapped[int] = mapped_column(Integer, default=30)
    target_calories: Mapped[int] = mapped_column(Integer, default=2000)
    target_water_ml: Mapped[int] = mapped_column(Integer, default=2000)
    target_sleep_hours: Mapped[float] = mapped_column(Float, default=8.0)

    # Gamification
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[str] = mapped_column(String(20), default="Bronze")  # Bronze/Silver/Gold/Platinum
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_active_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Profile
    profile_photo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    allow_social_sharing: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public_profile: Mapped[bool] = mapped_column(Boolean, default=True)

    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    sessions: Mapped[list[ExerciseSession]] = relationship("ExerciseSession", back_populates="user")
    recommendations: Mapped[list[Recommendation]] = relationship("Recommendation", back_populates="user")
    progress: Mapped[list[HistoricalProgress]] = relationship("HistoricalProgress", back_populates="user")
    daily_logs: Mapped[list[DailyHealthLog]] = relationship("DailyHealthLog", back_populates="user")
    food_logs: Mapped[list[FoodLog]] = relationship("FoodLog", back_populates="user")
    water_logs: Mapped[list[WaterLog]] = relationship("WaterLog", back_populates="user")
    achievements: Mapped[list[UserAchievement]] = relationship("UserAchievement", back_populates="user")
    favorites: Mapped[list[Favorite]] = relationship("Favorite", back_populates="user")
    social_posts: Mapped[list[SocialPost]] = relationship("SocialPost", back_populates="user")
    notifications: Mapped[list[Notification]] = relationship("Notification", back_populates="user")
    health_reports: Mapped[list[AIHealthReport]] = relationship("AIHealthReport", back_populates="user")
    following: Mapped[list[Follower]] = relationship("Follower", foreign_keys="[Follower.follower_id]", back_populates="follower")
    followers: Mapped[list[Follower]] = relationship("Follower", foreign_keys="[Follower.followee_id]", back_populates="followee")


# ── Exercise Library ───────────────────────────────────────────────────────────

class ExerciseLibrary(Base):
    __tablename__ = "exercise_library"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)       # baduanjin | breathing | meditation
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_zh: Mapped[str | None] = mapped_column(String(100), nullable=True) # Chinese name
    difficulty: Mapped[str] = mapped_column(String(20), default="beginner") # beginner | intermediate | advanced
    duration_seconds: Mapped[int] = mapped_column(Integer, default=60)
    calories_est: Mapped[float] = mapped_column(Float, default=5.0)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    landmark_template: Mapped[str | None] = mapped_column(String(255), nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)       # JSON list
    target_joints: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    action_no: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 1-8 for Ba Duan Jin

    favorites: Mapped[list[Favorite]] = relationship("Favorite", back_populates="exercise")


# ── Exercise Session (extended) ────────────────────────────────────────────────

class ExerciseSession(Base):
    __tablename__ = "exercise_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profile.id"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    movement_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extended fields
    session_type: Mapped[str] = mapped_column(String(30), default="guided")
    # guided | practice | challenge | assessment
    device_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    avg_fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    calories_burned: Mapped[float] = mapped_column(Float, default=0.0)
    fatigue_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-1
    hydration_during_session: Mapped[int] = mapped_column(Integer, default=0)  # ml
    completed: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship("User", back_populates="sessions")
    pose_scores: Mapped[list[PoseScore]] = relationship("PoseScore", back_populates="session")
    session_actions: Mapped[list[SessionAction]] = relationship("SessionAction", back_populates="session")


# ── Pose Score ────────────────────────────────────────────────────────────────

class PoseScore(Base):
    __tablename__ = "pose_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercise_sessions.id"), nullable=False)
    movement_name: Mapped[str] = mapped_column(String(100), nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[ExerciseSession] = relationship("ExerciseSession", back_populates="pose_scores")


# ── Session Action (per-movement analytics) ────────────────────────────────────

class SessionAction(Base):
    __tablename__ = "session_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercise_sessions.id"), nullable=False)
    action_no: Mapped[int] = mapped_column(Integer, nullable=False)          # 1-8
    action_name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_ts: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_ts: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rep_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_score: Mapped[float] = mapped_column(Float, default=0.0)
    max_score: Mapped[float] = mapped_column(Float, default=0.0)
    advice_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    fatigue_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    completion_pct: Mapped[float] = mapped_column(Float, default=100.0)

    session: Mapped[ExerciseSession] = relationship("ExerciseSession", back_populates="session_actions")
    joint_metrics: Mapped[list[JointMetric]] = relationship("JointMetric", back_populates="session_action")


# ── Joint Metrics (biomechanical analytics) ────────────────────────────────────

class JointMetric(Base):
    __tablename__ = "joint_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_action_id: Mapped[int] = mapped_column(Integer, ForeignKey("session_actions.id"), nullable=False)
    joint_name: Mapped[str] = mapped_column(String(50), nullable=False)
    # shoulder_l, shoulder_r, elbow_l, elbow_r, hip_l, hip_r, knee_l, knee_r, spine, neck
    avg_angle: Mapped[float] = mapped_column(Float, default=0.0)
    min_angle: Mapped[float] = mapped_column(Float, default=0.0)
    max_angle: Mapped[float] = mapped_column(Float, default=0.0)
    std_dev: Mapped[float] = mapped_column(Float, default=0.0)
    symmetry_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-1

    session_action: Mapped[SessionAction] = relationship("SessionAction", back_populates="joint_metrics")


# ── Daily Health Log ───────────────────────────────────────────────────────────

class DailyHealthLog(Base):
    __tablename__ = "daily_health_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profile.id"), nullable=False)
    log_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    calories_consumed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    water_ml: Mapped[int] = mapped_column(Integer, default=0)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    stress_level: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-10
    mood: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # great | good | neutral | low | anxious
    steps: Mapped[int] = mapped_column(Integer, default=0)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="daily_logs")


# ── Food Log ───────────────────────────────────────────────────────────────────

class FoodLog(Base):
    __tablename__ = "food_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profile.id"), nullable=False)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)  # breakfast|lunch|dinner|snack
    food_name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    calories: Mapped[float] = mapped_column(Float, default=0.0)
    protein_g: Mapped[float] = mapped_column(Float, default=0.0)
    carbs_g: Mapped[float] = mapped_column(Float, default=0.0)
    fat_g: Mapped[float] = mapped_column(Float, default=0.0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="food_logs")


# ── Water Log ─────────────────────────────────────────────────────────────────

class WaterLog(Base):
    __tablename__ = "water_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profile.id"), nullable=False)
    amount_ml: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="water_logs")


# ── Achievements ───────────────────────────────────────────────────────────────

class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    badge_icon: Mapped[str] = mapped_column(String(10), nullable=False)   # emoji or icon key
    points: Mapped[int] = mapped_column(Integer, default=50)
    category: Mapped[str] = mapped_column(String(30), default="general")
    # streak | accuracy | reps | wellness | social | special
    condition_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # streak_days | total_sessions | total_reps | avg_score | water_days | etc.
    condition_value: Mapped[float] = mapped_column(Float, nullable=False)

    user_achievements: Mapped[list[UserAchievement]] = relationship("UserAchievement", back_populates="achievement")


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profile.id"), nullable=False)
    achievement_id: Mapped[int] = mapped_column(Integer, ForeignKey("achievements.id"), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="achievements")
    achievement: Mapped[Achievement] = relationship("Achievement", back_populates="user_achievements")


# ── Favorites ─────────────────────────────────────────────────────────────────

class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profile.id"), nullable=False)
    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercise_library.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="favorites")
    exercise: Mapped[ExerciseLibrary] = relationship("ExerciseLibrary", back_populates="favorites")


# ── Social Posts ──────────────────────────────────────────────────────────────

class SocialPost(Base):
    __tablename__ = "social_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profile.id"), nullable=False)
    post_type: Mapped[str] = mapped_column(String(30), default="session")
    # session | achievement | streak | weekly_summary
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("exercise_sessions.id"), nullable=True)
    achievement_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("achievements.id"), nullable=True)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="social_posts")


# ── Followers ─────────────────────────────────────────────────────────────────

class Follower(Base):
    __tablename__ = "followers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    follower_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profile.id"), nullable=False)
    followee_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profile.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    follower: Mapped[User] = relationship("User", foreign_keys=[follower_id], back_populates="following")
    followee: Mapped[User] = relationship("User", foreign_keys=[followee_id], back_populates="followers")


# ── Notifications ──────────────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profile.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    # achievement | streak | reminder | social | report
    content: Mapped[str] = mapped_column(Text, nullable=False)
    read_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="notifications")


# ── AI Health Reports ──────────────────────────────────────────────────────────

class AIHealthReport(Base):
    __tablename__ = "ai_health_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profile.id"), nullable=False)
    posture_trend: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # improving | stable | declining
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-10
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="health_reports")


# ── Legacy tables kept for backward compatibility ──────────────────────────────

class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profile.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="recommendations")


class HistoricalProgress(Base):
    __tablename__ = "historical_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profile.id"), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    avg_score: Mapped[float] = mapped_column(Float, default=0.0)
    sessions_count: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship("User", back_populates="progress")


# ── Recommendation Rules (admin-managed Yangsheng advice) ─────────────────────

class RecommendationRule(Base):
    __tablename__ = "recommendation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # e.g. high_stress, low_sessions, low_accuracy, poor_sleep, default
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    condition_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    advice_text: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
