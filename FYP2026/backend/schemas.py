from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=6)
    age: int | None = Field(None, ge=1, le=120)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    id: int
    username: str
    email: str
    email_verified: bool
    age: int | None
    gender: str | None
    height_cm: float | None
    weight_kg: float | None
    bmi: float | None
    stress_level: int | None
    sleep_quality: int | None
    target_goal: str | None
    activity_level: str | None
    health_conditions: str | None
    exercise_preferences: str | None
    target_exercise_minutes: int
    target_calories: int
    target_water_ml: int
    target_sleep_hours: float
    total_points: int
    level: str
    streak_days: int
    profile_photo: str | None
    allow_social_sharing: bool
    is_public_profile: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    age: int | None = Field(None, ge=1, le=120)
    gender: str | None = None
    height_cm: float | None = Field(None, ge=50, le=300)
    weight_kg: float | None = Field(None, ge=10, le=500)
    stress_level: int | None = Field(None, ge=1, le=5)
    sleep_quality: int | None = Field(None, ge=1, le=5)
    target_goal: str | None = None
    activity_level: str | None = None
    health_conditions: str | None = None
    exercise_preferences: str | None = None
    target_exercise_minutes: int | None = Field(None, ge=5, le=480)
    target_calories: int | None = Field(None, ge=500, le=10000)
    target_water_ml: int | None = Field(None, ge=500, le=10000)
    target_sleep_hours: float | None = Field(None, ge=3, le=14)
    allow_social_sharing: bool | None = None
    is_public_profile: bool | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


# ── Exercise Library ──────────────────────────────────────────────────────────

class ExerciseLibraryOut(BaseModel):
    id: int
    category: str
    name: str
    name_zh: str | None
    difficulty: str
    duration_seconds: int
    calories_est: float
    description: str | None
    benefits: str | None
    target_joints: str | None
    action_no: int | None
    thumbnail: str | None

    model_config = {"from_attributes": True}


# ── Sessions ──────────────────────────────────────────────────────────────────

class PoseScoreCreate(BaseModel):
    movement_name: str
    accuracy: float = Field(..., ge=0, le=100)


class PoseScoreOut(BaseModel):
    id: int
    movement_name: str
    accuracy: float
    timestamp: datetime

    model_config = {"from_attributes": True}


class SessionActionCreate(BaseModel):
    action_no: int
    action_name: str
    rep_count: int = 0
    avg_score: float = 0.0
    max_score: float = 0.0
    advice_summary: str | None = None
    fatigue_score: float | None = None
    completion_pct: float = 100.0


class JointMetricCreate(BaseModel):
    joint_name: str
    avg_angle: float
    min_angle: float
    max_angle: float
    std_dev: float
    symmetry_score: float | None = None


class JointMetricOut(BaseModel):
    id: int
    joint_name: str
    avg_angle: float
    min_angle: float
    max_angle: float
    std_dev: float
    symmetry_score: float | None

    model_config = {"from_attributes": True}


class SessionActionOut(BaseModel):
    id: int
    action_no: int
    action_name: str
    start_ts: datetime | None
    end_ts: datetime | None
    rep_count: int
    avg_score: float
    max_score: float
    advice_summary: str | None
    fatigue_score: float | None
    completion_pct: float
    joint_metrics: list[JointMetricOut] = []

    model_config = {"from_attributes": True}


class SessionCreate(BaseModel):
    duration_seconds: int = Field(..., ge=0)
    pose_scores: list[PoseScoreCreate] = []
    session_actions: list[SessionActionCreate] = []
    notes: str | None = None
    session_type: str = "guided"
    calories_burned: float = 0.0
    fatigue_score: float | None = None


class SessionOut(BaseModel):
    id: int
    date: datetime
    duration_seconds: int
    total_score: float
    movement_count: int
    notes: str | None
    session_type: str
    calories_burned: float
    fatigue_score: float | None
    pose_scores: list[PoseScoreOut] = []
    session_actions: list[SessionActionOut] = []

    model_config = {"from_attributes": True}


# ── Dashboard ─────────────────────────────────────────────────────────────────

class WeeklyStats(BaseModel):
    sessions_this_week: int
    avg_accuracy: float
    best_accuracy: float
    total_minutes: int
    streak_days: int
    total_points: int
    level: str
    calories_burned_week: float


class ProgressPoint(BaseModel):
    date: str
    avg_score: float
    sessions: int


class MovementBreakdown(BaseModel):
    movement_name: str
    avg_accuracy: float
    count: int


class DashboardSummary(BaseModel):
    weekly_stats: WeeklyStats
    progress_history: list[ProgressPoint]
    movement_breakdown: list[MovementBreakdown]
    latest_recommendation: str | None
    recent_achievements: list[dict]
    today_health: dict | None


# ── Recommendations ───────────────────────────────────────────────────────────

class RecommendationOut(BaseModel):
    id: int
    content: str
    generated_at: datetime

    model_config = {"from_attributes": True}


class GenerateRecommendationRequest(BaseModel):
    force_refresh: bool = False


# ── Wellness / Health Logs ────────────────────────────────────────────────────

class DailyHealthLogCreate(BaseModel):
    log_date: datetime
    calories_consumed: int | None = None
    water_ml: int = 0
    sleep_hours: float | None = None
    stress_level: int | None = Field(None, ge=1, le=10)
    mood: str | None = None
    steps: int = 0
    weight_kg: float | None = None
    notes: str | None = None


class DailyHealthLogOut(BaseModel):
    id: int
    log_date: datetime
    calories_consumed: int | None
    water_ml: int
    sleep_hours: float | None
    stress_level: int | None
    mood: str | None
    steps: int
    weight_kg: float | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FoodLogCreate(BaseModel):
    meal_type: str
    food_name: str
    quantity: str | None = None
    calories: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0


class FoodLogOut(BaseModel):
    id: int
    meal_type: str
    food_name: str
    quantity: str | None
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    timestamp: datetime

    model_config = {"from_attributes": True}


class WaterLogCreate(BaseModel):
    amount_ml: int = Field(..., ge=50, le=2000)


class WaterLogOut(BaseModel):
    id: int
    amount_ml: int
    timestamp: datetime

    model_config = {"from_attributes": True}


# ── Gamification ──────────────────────────────────────────────────────────────

class AchievementOut(BaseModel):
    id: int
    title: str
    description: str
    badge_icon: str
    points: int
    category: str

    model_config = {"from_attributes": True}


class UserAchievementOut(BaseModel):
    id: int
    achievement: AchievementOut
    earned_at: datetime

    model_config = {"from_attributes": True}


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    profile_photo: str | None
    total_points: int
    level: str
    streak_days: int


# ── Social ─────────────────────────────────────────────────────────────────────

class SocialPostCreate(BaseModel):
    post_type: str = "session"
    caption: str | None = None
    session_id: int | None = None
    achievement_id: int | None = None


class SocialPostOut(BaseModel):
    id: int
    post_type: str
    image_url: str | None
    caption: str | None
    likes: int
    created_at: datetime
    username: str
    profile_photo: str | None

    model_config = {"from_attributes": True}


class FavoriteOut(BaseModel):
    id: int
    exercise: ExerciseLibraryOut
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Notifications ─────────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: int
    type: str
    content: str
    read_flag: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── AI Health Reports ─────────────────────────────────────────────────────────

class AIHealthReportOut(BaseModel):
    id: int
    posture_trend: str | None
    risk_score: float | None
    recommendation: str | None
    summary: str
    generated_at: datetime

    model_config = {"from_attributes": True}


# ── Pose WebSocket frames ─────────────────────────────────────────────────────

class PoseFrameResult(BaseModel):
    accuracy: float | None
    action_label: str | None
    action_confidence: float
    advice: list[str]
    landmarks: list[dict] | None


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminUserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_suspended: bool
    age: int | None
    gender: str | None
    total_points: int
    level: str
    streak_days: int
    created_at: datetime
    session_count: int = 0

    model_config = {"from_attributes": True}


class AdminUserUpdate(BaseModel):
    role: str | None = None
    is_suspended: bool | None = None


class AdminSessionOut(BaseModel):
    id: int
    user_id: int
    username: str
    date: datetime
    duration_seconds: int
    total_score: float
    movement_count: int
    session_type: str
    calories_burned: float
    completed: bool

    model_config = {"from_attributes": True}


class AdminSessionDetail(BaseModel):
    id: int
    user_id: int
    username: str
    date: datetime
    duration_seconds: int
    total_score: float
    movement_count: int
    session_type: str
    calories_burned: float
    fatigue_score: float | None
    completed: bool
    pose_scores: list[PoseScoreOut] = []
    session_actions: list[SessionActionOut] = []

    model_config = {"from_attributes": True}


class RecommendationRuleOut(BaseModel):
    id: int
    key: str
    label: str
    condition_description: str | None
    advice_text: str
    priority: int
    is_active: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecommendationRuleCreate(BaseModel):
    key: str = Field(..., min_length=2, max_length=50)
    label: str = Field(..., min_length=2, max_length=100)
    condition_description: str | None = None
    advice_text: str = Field(..., min_length=10)
    priority: int = 0
    is_active: bool = True


class RecommendationRuleUpdate(BaseModel):
    label: str | None = None
    condition_description: str | None = None
    advice_text: str | None = None
    priority: int | None = None
    is_active: bool | None = None


class AdminUsageStats(BaseModel):
    total_users: int
    active_users_7d: int
    total_sessions: int
    sessions_7d: int
    avg_session_score: float
    total_recommendations_generated: int
    suspended_users: int


class AdminAccuracyStats(BaseModel):
    overall_avg_accuracy: float
    movement_accuracy: list[dict]
    accuracy_trend: list[dict]


class AdminModelEvalLog(BaseModel):
    date: str
    total_frames: int
    avg_confidence: float
    low_confidence_pct: float
    actions_detected: dict
