"""
Seed the database with 10+ users and all new table data.
    python seed_data.py
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta

from dotenv import load_dotenv
load_dotenv()

from backend.database import SessionLocal, init_db
from backend.auth import hash_password
from backend import models

# ── Constants ─────────────────────────────────────────────────────────────────

MOVEMENTS = [
    "Two Hands Hold up the Heavens",
    "Drawing the Bow",
    "Separate Heaven and Earth",
    "Wise Owl Gazes Backward",
    "Sway the Head and Shake the Tail",
    "Two Hands Hold the Feet",
    "Clench the Fists",
    "Bouncing on the Toes",
]

JOINT_NAMES = [
    "shoulder_l", "shoulder_r", "elbow_l", "elbow_r",
    "hip_l", "hip_r", "knee_l", "knee_r", "spine", "neck",
]

USERS = [
    {
        "username": "Jungkook",    "email": "jk@gmail.com",        "password": "abc123",
        "age": 25, "gender": "male",   "height_cm": 178, "weight_kg": 70,
        "target_goal": "improve_posture",  "activity_level": "active",
        "stress_level": 2, "sleep_quality": 4,
        "health_conditions": json.dumps([]),
        "base_acc": 78, "sessions_per_week": 5,
    },
    {
        "username": "MingLi",      "email": "mli@gmail.com",        "password": "abc123",
        "age": 45, "gender": "female", "height_cm": 162, "weight_kg": 58,
        "target_goal": "stress_relief",   "activity_level": "moderate",
        "stress_level": 4, "sleep_quality": 2,
        "health_conditions": json.dumps(["neck_pain", "shoulder_pain"]),
        "base_acc": 65, "sessions_per_week": 3,
    },
    {
        "username": "SarahTan",    "email": "sarah@gmail.com",      "password": "abc123",
        "age": 33, "gender": "female", "height_cm": 165, "weight_kg": 62,
        "target_goal": "maintain_health", "activity_level": "moderate",
        "stress_level": 3, "sleep_quality": 3,
        "health_conditions": json.dumps([]),
        "base_acc": 72, "sessions_per_week": 4,
    },
    {
        "username": "DrWei",       "email": "wei@hospital.com",     "password": "abc123",
        "age": 52, "gender": "male",   "height_cm": 172, "weight_kg": 75,
        "target_goal": "improve_flexibility", "activity_level": "light",
        "stress_level": 5, "sleep_quality": 2,
        "health_conditions": json.dumps(["hypertension", "lumbar_discomfort"]),
        "base_acc": 60, "sessions_per_week": 2,
    },
    {
        "username": "YukiNakamura","email": "yuki@jp.com",          "password": "abc123",
        "age": 29, "gender": "female", "height_cm": 158, "weight_kg": 50,
        "target_goal": "improve_flexibility", "activity_level": "very_active",
        "stress_level": 2, "sleep_quality": 4,
        "health_conditions": json.dumps([]),
        "base_acc": 85, "sessions_per_week": 6,
    },
    {
        "username": "AhmedHassan", "email": "ahmed@eg.com",         "password": "abc123",
        "age": 38, "gender": "male",   "height_cm": 180, "weight_kg": 85,
        "target_goal": "lose_weight",     "activity_level": "moderate",
        "stress_level": 3, "sleep_quality": 3,
        "health_conditions": json.dumps(["knee_pain"]),
        "base_acc": 68, "sessions_per_week": 3,
    },
    {
        "username": "LinaNguyen",  "email": "lina@vn.com",          "password": "abc123",
        "age": 22, "gender": "female", "height_cm": 155, "weight_kg": 48,
        "target_goal": "improve_posture", "activity_level": "active",
        "stress_level": 2, "sleep_quality": 5,
        "health_conditions": json.dumps([]),
        "base_acc": 80, "sessions_per_week": 5,
    },
    {
        "username": "PakornT",     "email": "pakorn@th.com",        "password": "abc123",
        "age": 41, "gender": "male",   "height_cm": 170, "weight_kg": 72,
        "target_goal": "stress_relief",   "activity_level": "sedentary",
        "stress_level": 4, "sleep_quality": 3,
        "health_conditions": json.dumps(["neck_pain"]),
        "base_acc": 62, "sessions_per_week": 2,
    },
    {
        "username": "ChenXiaomei", "email": "xiaomei@cn.com",       "password": "abc123",
        "age": 60, "gender": "female", "height_cm": 158, "weight_kg": 56,
        "target_goal": "maintain_health", "activity_level": "light",
        "stress_level": 2, "sleep_quality": 4,
        "health_conditions": json.dumps(["hypertension"]),
        "base_acc": 70, "sessions_per_week": 4,
    },
    {
        "username": "RajeshKumar", "email": "rajesh@in.com",        "password": "abc123",
        "age": 35, "gender": "male",   "height_cm": 175, "weight_kg": 80,
        "target_goal": "lose_weight",     "activity_level": "moderate",
        "stress_level": 3, "sleep_quality": 3,
        "health_conditions": json.dumps([]),
        "base_acc": 73, "sessions_per_week": 3,
    },
    {
        "username": "SofiaRossi",  "email": "sofia@it.com",         "password": "abc123",
        "age": 27, "gender": "female", "height_cm": 168, "weight_kg": 60,
        "target_goal": "stress_relief",   "activity_level": "active",
        "stress_level": 2, "sleep_quality": 4,
        "health_conditions": json.dumps([]),
        "base_acc": 82, "sessions_per_week": 5,
    },
    {
        "username": "MaxBecker",   "email": "max@de.com",           "password": "abc123",
        "age": 44, "gender": "male",   "height_cm": 185, "weight_kg": 90,
        "target_goal": "improve_posture", "activity_level": "light",
        "stress_level": 3, "sleep_quality": 3,
        "health_conditions": json.dumps(["lumbar_discomfort"]),
        "base_acc": 66, "sessions_per_week": 2,
    },
]

RECOMMENDATIONS = [
    "Great consistency this week! Focus on slow, deliberate breathing during Movement 1 to deepen the stretch.",
    "Your shoulder alignment in Drawing the Bow has improved. Try holding each position for an extra breath.",
    "Consider a short 10-minute morning session to build your streak. Even gentle movements activate circulation.",
    "Your practice frequency is excellent. Pay attention to knee alignment during Bouncing on the Toes.",
    "Evening sessions suit your rhythm well. Wind down with slower repetitions of Movement 4.",
    "Your posture score is improving steadily. Challenge yourself with the full 8-movement sequence today.",
    "Hydration is key for flexibility. Drink 250ml of water before your session for better joint mobility.",
    "Try the Assessment session mode to get a baseline of your posture and track progress over time.",
]

FOOD_ITEMS = [
    ("breakfast", "Oatmeal with berries", "1 bowl", 320),
    ("breakfast", "Green tea", "1 cup", 5),
    ("breakfast", "Wholegrain toast", "2 slices", 180),
    ("lunch", "Brown rice with tofu", "1 plate", 450),
    ("lunch", "Vegetable soup", "1 bowl", 150),
    ("lunch", "Grilled chicken breast", "150g", 280),
    ("dinner", "Stir-fried vegetables", "1 plate", 200),
    ("dinner", "Fish with quinoa", "1 plate", 420),
    ("dinner", "Lentil curry", "1 plate", 380),
    ("snack", "Apple", "1 medium", 80),
    ("snack", "Mixed nuts", "30g", 180),
    ("snack", "Greek yoghurt", "150g", 130),
]

MOODS = ["great", "good", "neutral", "low", "anxious"]

SOCIAL_CAPTIONS = [
    "Just completed all 8 Ba Duan Jin movements with a personal best score! 🎉",
    "30-day streak achieved! Consistency is everything on this wellness journey.",
    "Feeling so much more flexible after 2 weeks of daily practice. My back pain has reduced significantly!",
    "Today's session felt incredible. The Wise Owl movement is finally clicking for me.",
    "Started with 60% accuracy, now hitting 85% consistently. Progress is real! 💪",
    "Morning Ba Duan Jin is now my favourite way to start the day. Try it!",
    "Just unlocked the Posture Master badge after weeks of focused practice!",
    "Week 3 summary: 6 sessions, avg score 78%. Getting stronger every day 🌱",
]

EXERCISE_LIBRARY_DATA = [
    {
        "category": "baduanjin", "name": "Two Hands Hold up the Heavens", "name_zh": "双手托天理三焦",
        "difficulty": "beginner", "duration_seconds": 120, "calories_est": 8, "action_no": 1,
        "description": "Interlace fingers above head and stretch upward, regulating the Triple Warmer meridian.",
        "benefits": json.dumps(["Stretches spine", "Opens chest", "Improves posture", "Activates Triple Warmer"]),
        "target_joints": json.dumps(["shoulder", "wrist", "spine"]),
    },
    {
        "category": "baduanjin", "name": "Drawing the Bow", "name_zh": "左右开弓似射雕",
        "difficulty": "beginner", "duration_seconds": 150, "calories_est": 10, "action_no": 2,
        "description": "Simulate drawing a bow to each side, strengthening the lungs and opening the chest.",
        "benefits": json.dumps(["Strengthens arms", "Opens chest", "Improves lung capacity", "Balances left/right"]),
        "target_joints": json.dumps(["shoulder", "elbow", "wrist", "hip"]),
    },
    {
        "category": "baduanjin", "name": "Separate Heaven and Earth", "name_zh": "调理脾胃须单举",
        "difficulty": "beginner", "duration_seconds": 120, "calories_est": 9, "action_no": 3,
        "description": "Alternate pressing one hand up and one down to regulate the spleen and stomach.",
        "benefits": json.dumps(["Aids digestion", "Stretches side body", "Balances organs"]),
        "target_joints": json.dumps(["shoulder", "wrist", "spine", "hip"]),
    },
    {
        "category": "baduanjin", "name": "Wise Owl Gazes Backward", "name_zh": "五劳七伤往后瞧",
        "difficulty": "beginner", "duration_seconds": 120, "calories_est": 7, "action_no": 4,
        "description": "Slowly turn the head to look behind, relieving tension in the five viscera.",
        "benefits": json.dumps(["Relieves neck tension", "Improves cervical mobility", "Calms nervous system"]),
        "target_joints": json.dumps(["neck", "spine", "shoulder"]),
    },
    {
        "category": "baduanjin", "name": "Sway the Head and Shake the Tail", "name_zh": "摇头摆尾去心火",
        "difficulty": "intermediate", "duration_seconds": 150, "calories_est": 12, "action_no": 5,
        "description": "Bend forward in a horse stance and sway the head and hips to extinguish heart fire.",
        "benefits": json.dumps(["Strengthens legs", "Reduces stress", "Improves balance", "Opens hips"]),
        "target_joints": json.dumps(["hip", "knee", "spine", "neck"]),
    },
    {
        "category": "baduanjin", "name": "Two Hands Hold the Feet", "name_zh": "两手攀足固肾腰",
        "difficulty": "intermediate", "duration_seconds": 120, "calories_est": 11, "action_no": 6,
        "description": "Bend forward to touch the toes, tonifying the kidneys and strengthening the lumbar.",
        "benefits": json.dumps(["Strengthens kidneys", "Stretches hamstrings", "Relieves lower back pain"]),
        "target_joints": json.dumps(["spine", "hip", "knee", "ankle"]),
    },
    {
        "category": "baduanjin", "name": "Clench the Fists with Fierce Eyes", "name_zh": "攒拳怒目增气力",
        "difficulty": "intermediate", "duration_seconds": 150, "calories_est": 14, "action_no": 7,
        "description": "In horse stance, punch forward with intense focus to increase overall vitality.",
        "benefits": json.dumps(["Builds strength", "Increases energy", "Improves focus", "Strengthens legs"]),
        "target_joints": json.dumps(["shoulder", "elbow", "wrist", "hip", "knee"]),
    },
    {
        "category": "baduanjin", "name": "Bouncing on the Toes", "name_zh": "背后七颠百病消",
        "difficulty": "beginner", "duration_seconds": 90, "calories_est": 8, "action_no": 8,
        "description": "Rise on the toes and gently drop the heels to vibrate the spine and expel illness.",
        "benefits": json.dumps(["Improves balance", "Massages spine", "Boosts circulation", "Calms mind"]),
        "target_joints": json.dumps(["ankle", "knee", "spine"]),
    },
    {
        "category": "breathing", "name": "4-7-8 Breathing", "name_zh": "呼吸法",
        "difficulty": "beginner", "duration_seconds": 300, "calories_est": 2, "action_no": None,
        "description": "Inhale for 4 counts, hold for 7, exhale for 8. Activates the parasympathetic nervous system.",
        "benefits": json.dumps(["Reduces anxiety", "Improves sleep", "Lowers heart rate", "Calms mind"]),
        "target_joints": json.dumps([]),
    },
    {
        "category": "breathing", "name": "Box Breathing", "name_zh": "方形呼吸",
        "difficulty": "beginner", "duration_seconds": 240, "calories_est": 1, "action_no": None,
        "description": "Inhale, hold, exhale, hold each for 4 counts. Used by Navy SEALs for stress control.",
        "benefits": json.dumps(["Stress relief", "Mental clarity", "Nervous system reset"]),
        "target_joints": json.dumps([]),
    },
    {
        "category": "meditation", "name": "Body Scan Meditation", "name_zh": "身体扫描冥想",
        "difficulty": "beginner", "duration_seconds": 600, "calories_est": 3, "action_no": None,
        "description": "Systematically bring awareness to each part of the body from feet to head.",
        "benefits": json.dumps(["Deep relaxation", "Stress relief", "Body awareness", "Better sleep"]),
        "target_joints": json.dumps([]),
    },
    {
        "category": "meditation", "name": "Mindful Sitting Meditation", "name_zh": "正念冥想",
        "difficulty": "beginner", "duration_seconds": 900, "calories_est": 4, "action_no": None,
        "description": "Sit comfortably and observe breath and thoughts without judgement.",
        "benefits": json.dumps(["Improves focus", "Reduces stress", "Emotional balance", "Mental clarity"]),
        "target_joints": json.dumps([]),
    },
]

ACHIEVEMENTS_DATA = [
    # Streak achievements
    {"title": "First Step",        "description": "Complete your first session",        "badge_icon": "🌱", "points": 20,  "category": "streak",   "condition_type": "total_sessions", "condition_value": 1},
    {"title": "3-Day Streak",      "description": "Practice 3 days in a row",           "badge_icon": "🔥", "points": 30,  "category": "streak",   "condition_type": "streak_days",    "condition_value": 3},
    {"title": "7-Day Streak",      "description": "Practice 7 consecutive days",         "badge_icon": "⚡", "points": 75,  "category": "streak",   "condition_type": "streak_days",    "condition_value": 7},
    {"title": "30-Day Streak",     "description": "30 days of unbroken practice",        "badge_icon": "💎", "points": 300, "category": "streak",   "condition_type": "streak_days",    "condition_value": 30},
    # Session achievements
    {"title": "10 Sessions",       "description": "Complete 10 exercise sessions",       "badge_icon": "🏃", "points": 50,  "category": "general",  "condition_type": "total_sessions", "condition_value": 10},
    {"title": "50 Sessions",       "description": "Complete 50 exercise sessions",       "badge_icon": "🎯", "points": 150, "category": "general",  "condition_type": "total_sessions", "condition_value": 50},
    {"title": "100 Sessions",      "description": "Complete 100 exercise sessions",      "badge_icon": "🏆", "points": 400, "category": "general",  "condition_type": "total_sessions", "condition_value": 100},
    # Rep achievements
    {"title": "First 100 Reps",    "description": "Complete 100 total repetitions",      "badge_icon": "💪", "points": 60,  "category": "reps",     "condition_type": "total_reps",     "condition_value": 100},
    {"title": "1000 Reps",         "description": "Complete 1,000 repetitions total",    "badge_icon": "🦾", "points": 200, "category": "reps",     "condition_type": "total_reps",     "condition_value": 1000},
    # Accuracy achievements
    {"title": "Posture Beginner",  "description": "Reach 70% average posture score",     "badge_icon": "🧘", "points": 50,  "category": "accuracy", "condition_type": "avg_score",      "condition_value": 70},
    {"title": "Posture Adept",     "description": "Reach 80% average posture score",     "badge_icon": "✨", "points": 100, "category": "accuracy", "condition_type": "avg_score",      "condition_value": 80},
    {"title": "Posture Master",    "description": "Reach 90% average posture score",     "badge_icon": "🌟", "points": 250, "category": "accuracy", "condition_type": "avg_score",      "condition_value": 90},
    # Wellness achievements
    {"title": "Hydration Hero",    "description": "Log 2000ml water on 5 days",          "badge_icon": "💧", "points": 80,  "category": "wellness", "condition_type": "water_days",     "condition_value": 5},
    {"title": "Hydration Legend",  "description": "Log 2000ml water on 30 days",         "badge_icon": "🌊", "points": 200, "category": "wellness", "condition_type": "water_days",     "condition_value": 30},
    # Points
    {"title": "Rising Star",       "description": "Earn 500 points",                     "badge_icon": "⭐", "points": 0,   "category": "special",  "condition_type": "total_points",   "condition_value": 500},
    {"title": "Champion",          "description": "Earn 2000 points",                    "badge_icon": "🥇", "points": 0,   "category": "special",  "condition_type": "total_points",   "condition_value": 2000},
]


def rand_acc(base, noise=12.0):
    return round(min(99.0, max(40.0, base + random.gauss(0, noise))), 1)


def seed():
    init_db()
    db = SessionLocal()

    existing = db.query(models.User).count()
    if existing > 0:
        print(f"Database already has {existing} user(s). Skipping seed.")
        print("Delete baduanjin.db and re-run for a fresh seed.")
        db.close()
        return

    # ── Seed exercise library ─────────────────────────────────────────────────
    print("Seeding exercise library…")
    exercise_objs = {}
    for ex_data in EXERCISE_LIBRARY_DATA:
        ex = models.ExerciseLibrary(**ex_data)
        db.add(ex)
        db.flush()
        exercise_objs[ex.name] = ex
    db.commit()
    print(f"  Added {len(exercise_objs)} exercises")

    # ── Seed achievements ─────────────────────────────────────────────────────
    print("Seeding achievements…")
    achievement_objs = []
    for a_data in ACHIEVEMENTS_DATA:
        a = models.Achievement(**a_data)
        db.add(a)
        db.flush()
        achievement_objs.append(a)
    db.commit()
    print(f"  Added {len(achievement_objs)} achievements")

    # ── Seed users ────────────────────────────────────────────────────────────
    print("\nSeeding users…")
    user_objs = []
    now = datetime.utcnow()

    for u_data in USERS:
        base_acc = u_data.pop("base_acc")
        sessions_per_week = u_data.pop("sessions_per_week")

        h = u_data.get("height_cm")
        w = u_data.get("weight_kg")
        bmi = round(w / ((h / 100) ** 2), 1) if h and w else None

        # Streak calculation
        streak = min(sessions_per_week * 4, 28)
        points = random.randint(sessions_per_week * 80, sessions_per_week * 200)
        level = "Bronze"
        if points >= 3000: level = "Platinum"
        elif points >= 1500: level = "Gold"
        elif points >= 500: level = "Silver"

        user = models.User(
            username=u_data["username"],
            email=u_data["email"],
            password_hash=hash_password(u_data["password"]),
            age=u_data.get("age"),
            gender=u_data.get("gender"),
            height_cm=h,
            weight_kg=w,
            bmi=bmi,
            target_goal=u_data.get("target_goal"),
            activity_level=u_data.get("activity_level"),
            stress_level=u_data.get("stress_level"),
            sleep_quality=u_data.get("sleep_quality"),
            health_conditions=u_data.get("health_conditions"),
            target_exercise_minutes=random.choice([20, 30, 45, 60]),
            target_calories=random.choice([1800, 2000, 2200, 2500]),
            target_water_ml=random.choice([1500, 2000, 2500]),
            target_sleep_hours=random.choice([7.0, 7.5, 8.0]),
            total_points=points,
            level=level,
            streak_days=streak,
            last_active_date=now - timedelta(hours=random.randint(1, 20)),
            email_verified=True,
            allow_social_sharing=True,
            is_public_profile=True,
        )
        db.add(user)
        db.flush()
        user_objs.append((user, base_acc, sessions_per_week))

        # Sessions (28 days of history)
        current_acc = base_acc
        daily_totals: dict[str, list[float]] = {}

        for day_offset in range(28, 0, -1):
            session_date = now - timedelta(days=day_offset)
            sessions_today = random.randint(1, 2) if random.random() < (sessions_per_week / 7) else 0

            for _ in range(sessions_today):
                session_type = random.choice(["guided", "guided", "practice", "assessment"])
                duration = random.randint(8 * 60, 25 * 60)
                calories = round(duration / 60 * random.uniform(3.5, 6.0), 1)

                session = models.ExerciseSession(
                    user_id=user.id,
                    duration_seconds=duration,
                    date=session_date + timedelta(hours=random.randint(6, 21)),
                    session_type=session_type,
                    calories_burned=calories,
                    fatigue_score=round(random.uniform(0.1, 0.7), 2),
                )
                db.add(session)
                db.flush()

                # Pose scores
                scores = []
                selected_movements = random.sample(MOVEMENTS, k=random.randint(4, 8))
                for mv in selected_movements:
                    acc = rand_acc(current_acc)
                    db.add(models.PoseScore(
                        session_id=session.id,
                        movement_name=mv,
                        accuracy=acc,
                        timestamp=session.date,
                    ))
                    scores.append(acc)

                session.total_score = round(sum(scores) / len(scores), 2)
                session.movement_count = len(scores)

                # Session actions (per-movement detail)
                for i, (mv, acc) in enumerate(zip(selected_movements, scores)):
                    action_start = session.date + timedelta(seconds=i * (duration // len(selected_movements)))
                    action_end = action_start + timedelta(seconds=duration // len(selected_movements))
                    sa = models.SessionAction(
                        session_id=session.id,
                        action_no=MOVEMENTS.index(mv) + 1,
                        action_name=mv,
                        start_ts=action_start,
                        end_ts=action_end,
                        rep_count=random.randint(4, 12),
                        avg_score=acc,
                        max_score=min(99, acc + random.uniform(2, 8)),
                        advice_summary=json.dumps(["Focus on breathing", "Keep shoulders relaxed"] if acc < 75 else ["Good form!"]),
                        fatigue_score=round(random.uniform(0.1, 0.5), 2),
                        completion_pct=random.choice([80, 90, 100, 100]),
                    )
                    db.add(sa)
                    db.flush()

                    # Joint metrics for each action
                    for joint in random.sample(JOINT_NAMES, k=random.randint(4, 8)):
                        avg_angle = random.uniform(30, 150)
                        db.add(models.JointMetric(
                            session_action_id=sa.id,
                            joint_name=joint,
                            avg_angle=round(avg_angle, 1),
                            min_angle=round(avg_angle - random.uniform(5, 25), 1),
                            max_angle=round(avg_angle + random.uniform(5, 25), 1),
                            std_dev=round(random.uniform(2, 15), 2),
                            symmetry_score=round(random.uniform(0.6, 1.0), 2),
                        ))

                day_key = session_date.strftime("%Y-%m-%d")
                daily_totals.setdefault(day_key, []).append(session.total_score)

            current_acc = min(current_acc + random.uniform(0.2, 0.7), 95.0)

        # Historical progress
        for day_str, day_scores in daily_totals.items():
            db.add(models.HistoricalProgress(
                user_id=user.id,
                date=datetime.strptime(day_str, "%Y-%m-%d"),
                avg_score=round(sum(day_scores) / len(day_scores), 2),
                sessions_count=len(day_scores),
            ))

        # Recommendations
        for i, content in enumerate(random.sample(RECOMMENDATIONS, k=min(5, len(RECOMMENDATIONS)))):
            db.add(models.Recommendation(
                user_id=user.id,
                content=content,
                generated_at=now - timedelta(days=i),
            ))

        # Daily health logs (last 14 days)
        for day_offset in range(14, 0, -1):
            log_date = now - timedelta(days=day_offset)
            if random.random() < 0.75:
                water_ml = random.randint(1200, 3000)
                db.add(models.DailyHealthLog(
                    user_id=user.id,
                    log_date=log_date,
                    calories_consumed=random.randint(1400, 2800),
                    water_ml=water_ml,
                    sleep_hours=round(random.uniform(5.5, 9.0), 1),
                    stress_level=random.randint(1, 9),
                    mood=random.choice(MOODS),
                    steps=random.randint(2000, 12000),
                    weight_kg=w + random.uniform(-1.0, 1.0) if w else None,
                ))

                # Water logs
                for _ in range(random.randint(3, 8)):
                    db.add(models.WaterLog(
                        user_id=user.id,
                        amount_ml=random.choice([150, 200, 250, 300, 350]),
                        timestamp=log_date + timedelta(hours=random.randint(7, 21)),
                    ))

        # Food logs (last 7 days)
        for day_offset in range(7, 0, -1):
            log_date = now - timedelta(days=day_offset)
            for meal_type, food_name, qty, cal in random.sample(FOOD_ITEMS, k=random.randint(3, 6)):
                db.add(models.FoodLog(
                    user_id=user.id,
                    meal_type=meal_type,
                    food_name=food_name,
                    quantity=qty,
                    calories=cal + random.randint(-20, 20),
                    timestamp=log_date + timedelta(hours=random.randint(7, 21)),
                ))

        # Social posts
        if user.allow_social_sharing:
            for caption in random.sample(SOCIAL_CAPTIONS, k=random.randint(2, 4)):
                post_type = random.choice(["session", "achievement", "streak", "weekly_summary"])
                db.add(models.SocialPost(
                    user_id=user.id,
                    post_type=post_type,
                    caption=caption,
                    likes=random.randint(0, 45),
                    created_at=now - timedelta(days=random.randint(0, 14)),
                ))

        # Favorites
        fav_exercises = random.sample(EXERCISE_LIBRARY_DATA[:8], k=random.randint(2, 5))
        for ex_data in fav_exercises:
            ex_obj = exercise_objs.get(ex_data["name"])
            if ex_obj:
                db.add(models.Favorite(user_id=user.id, exercise_id=ex_obj.id))

        # Notifications
        notif_templates = [
            ("achievement", "You earned the 'First Step' badge! 🌱"),
            ("streak", f"🔥 You're on a {streak}-day streak! Keep it up!"),
            ("reminder", "Time for your daily Ba Duan Jin practice."),
            ("report", "Your weekly health report is ready. Check it out!"),
        ]
        for n_type, n_content in random.sample(notif_templates, k=random.randint(2, 4)):
            db.add(models.Notification(
                user_id=user.id,
                type=n_type,
                content=n_content,
                read_flag=random.choice([True, True, False]),
                created_at=now - timedelta(days=random.randint(0, 7)),
            ))

        # AI health reports
        for week in range(1, 4):
            trend = random.choice(["improving", "stable", "declining"])
            risk = round(random.uniform(0.5, 5.0), 1)
            db.add(models.AIHealthReport(
                user_id=user.id,
                posture_trend=trend,
                risk_score=risk,
                recommendation="• Focus on deep breathing during exercises.\n• Maintain your current practice frequency.",
                summary=(
                    f"Weekly Health Report — {(now - timedelta(weeks=week)).strftime('%Y-%m-%d')}\n"
                    f"Sessions: {random.randint(2, 7)} | Avg score: {round(current_acc, 1)}%\n"
                    f"Posture trend: {trend.title()}"
                ),
                generated_at=now - timedelta(weeks=week),
            ))

        db.commit()
        print(f"  Created user: {user.username}")

    # ── Seed followers ────────────────────────────────────────────────────────
    print("\nSeeding follower relationships…")
    for i, (follower, _, _) in enumerate(user_objs):
        # Each user follows 2-5 others
        others = [u for j, (u, _, _) in enumerate(user_objs) if j != i]
        for followee in random.sample(others, k=min(random.randint(2, 5), len(others))):
            existing = db.query(models.Follower).filter(
                models.Follower.follower_id == follower.id,
                models.Follower.followee_id == followee.id,
            ).first()
            if not existing:
                db.add(models.Follower(follower_id=follower.id, followee_id=followee.id))
    db.commit()

    # ── Seed user achievements ────────────────────────────────────────────────
    print("Seeding user achievements…")
    for user, base_acc, sessions_per_week in user_objs:
        total_sessions = db.query(models.ExerciseSession).filter(
            models.ExerciseSession.user_id == user.id
        ).count()
        avg_score = base_acc

        for achievement in achievement_objs:
            should_earn = False
            ct = achievement.condition_type
            cv = achievement.condition_value
            if ct == "streak_days" and user.streak_days >= cv:
                should_earn = True
            elif ct == "total_sessions" and total_sessions >= cv:
                should_earn = True
            elif ct == "avg_score" and avg_score >= cv:
                should_earn = True
            elif ct == "total_points" and user.total_points >= cv:
                should_earn = True

            if should_earn:
                db.add(models.UserAchievement(
                    user_id=user.id,
                    achievement_id=achievement.id,
                    earned_at=now - timedelta(days=random.randint(0, 20)),
                ))
    db.commit()
    print("  Done!")

    db.close()
    print(f"\nSeed complete: {len(USERS)} users, {len(EXERCISE_LIBRARY_DATA)} exercises, {len(ACHIEVEMENTS_DATA)} achievements")
    print("\nLogin credentials (all passwords: abc123):")
    for u in USERS:
        print(f"  {u['username']}")


if __name__ == "__main__":
    seed()
