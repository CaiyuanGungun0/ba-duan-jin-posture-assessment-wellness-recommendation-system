# Ba Duan Jin Digital Wellness Platform

A digital rehabilitation and wellness assistant built around Ba Duan Jin (八段锦 — Eight Pieces of Brocade) qigong. The platform combines real-time computer vision pose assessment with a personalised AI recommendation engine and a progress-tracking dashboard.

---

## System Overview

| Layer | Technology |
|---|---|
| Pose estimation | MediaPipe + CNN (MLP / Keras) |
| Backend API | FastAPI + SQLite (SQLAlchemy) |
| Frontend | React + Vite + Chart.js |
| AI recommendations | HuggingFace Inference API (Mistral-7B-Instruct) |
| Analytics | pandas |

### Workflow

1. User registers / logs in via the React frontend.
2. On the Session page the browser streams webcam frames to the backend WebSocket.
3. The backend runs MediaPipe pose detection and the CNN action classifier, returning live accuracy scores and skeleton overlay coordinates.
4. Session results (per-movement accuracy, duration) are saved to SQLite.
5. The LLM service builds a structured prompt from the user's session history and calls HuggingFace to generate a personalised daily recommendation.
6. The Dashboard displays a 14-day progress chart, movement accuracy breakdown, streak counter, and today's recommendation.

---

## Project Structure

```
FYP2026/
├── backend/                        # FastAPI application
│   ├── main.py                     # App entry point, CORS, lifespan
│   ├── database.py                 # SQLite engine (SQLAlchemy)
│   ├── models.py                   # ORM models
│   ├── schemas.py                  # Pydantic request / response schemas
│   ├── auth.py                     # JWT authentication + bcrypt
│   ├── routers/
│   │   ├── auth.py                 # POST /register, POST /login, GET /me
│   │   ├── sessions.py             # Exercise session CRUD
│   │   ├── dashboard.py            # Analytics summary
│   │   ├── recommendations.py      # LLM-generated daily advice
│   │   └── pose.py                 # WebSocket real-time pose stream
│   └── services/
│       ├── llm_service.py          # HuggingFace Inference API + rule-based fallback
│       └── analytics.py            # pandas stats, streak, movement breakdown
│
├── frontend/                       # React + Vite SPA
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx
│   │   │   ├── Dashboard.jsx       # Charts, stats, recommendation panel
│   │   │   └── Session.jsx         # Live webcam + skeleton overlay
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── CircularProgress.jsx
│   │   │   ├── RecommendationCard.jsx
│   │   │   └── SessionTimeline.jsx
│   │   └── services/
│   │       ├── api.js              # Axios client
│   │       └── auth.jsx            # AuthContext + AuthProvider
│   └── index.css                   # Design system 
│
├── pose_module/                    # Computer vision layer
│   ├── pose_detection.py           # Standalone webcam feedback (OpenCV)
│   ├── pose_model.py               # MLP + CNN action model wrappers
│   ├── posture_score.py            # Per-frame accuracy scoring
│   ├── feature_engineering.py      # Keypoint feature extraction
│   ├── extract_keypoints.py        # Offline keypoint extraction from video
│   ├── train_pose_model.py         # Model training script
│   ├── model_comparison.py         # MLP vs CNN benchmark
│   ├── augmentation.py             # Training data augmentation
│   └── evaluate_realtime.py        # Evaluation utilities
│
├── data/
│   ├── raw_video/                  # Reference Ba Duan Jin videos
│   └── keypoints/                  # Extracted keypoint CSV files
│
├── seed_data.py                    # Populates DB with 3 demo users + 28 days of sessions
├── requirements.txt
├── .env                            # HF_API_TOKEN and SECRET_KEY (not committed)
└── .gitignore
```

### Database Tables

| Table | Purpose |
|---|---|
| `user_profile` | Account info, age, stress/sleep self-report |
| `exercise_sessions` | Per-session duration, overall score, movement count |
| `pose_scores` | Per-movement accuracy within a session |
| `recommendations` | LLM-generated daily advice history |
| `historical_progress` | Daily aggregated score for chart rendering |

---

## Setup

### 1. Python environment

```powershell
pip install -r requirements.txt
```

### 2. Environment variables

Create a `.env` file in the project root:

```
HF_API_TOKEN=hf_your_token_here
SECRET_KEY=your-secret-key
```

Get a free HuggingFace read token at https://huggingface.co/settings/tokens.  
If `HF_API_TOKEN` is not set, the system falls back to rule-based recommendations automatically.

### 3. Seed demo data (optional)

```powershell
python seed_data.py
```

Creates 3 demo accounts with 28 days of simulated session history:

| Username | Password |
|---|---|
| Jungkook | abc123 |
| MingLi | abc123 |
| SarahTan | abc123 |

---

## Running the Application

### Backend

```powershell
uvicorn backend.main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

### Frontend

```powershell
cd frontend
npm install   # first time only
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Key API Endpoints

```
POST /api/auth/register         Register a new user
POST /api/auth/login            Login, returns JWT token
GET  /api/auth/me               Current user profile
PATCH /api/auth/me              Update age / stress / sleep ratings

POST /api/sessions/             Save a completed exercise session
GET  /api/sessions/             List recent sessions

GET  /api/dashboard/            Full dashboard summary (stats, charts, recommendation)

POST /api/recommendations/generate   Generate today's AI recommendation
GET  /api/recommendations/           Recommendation history

WS   /api/pose/stream           WebSocket — receives base64 JPEG frames,
                                 returns pose scores + landmark coordinates
```

---

## Pose Module (Standalone)

Extract reference keypoints from a video:

```powershell
python pose_module/extract_keypoints.py --video data/raw_video/baduanjin_video01.mp4 --output data/keypoints/video01_keypoints.csv
```

Run real-time pose feedback (OpenCV window):

```powershell
python pose_module/pose_detection.py --reference-video data/raw_video/baduanjin_video01.mp4 --reference-keypoints data/keypoints/video01_keypoints.csv
```

Train the action classifier:

```powershell
python pose_module/train_pose_model.py
```

---

## Disclaimer

This platform is for general wellness and rehabilitation assistance only. It does not diagnose medical conditions, prescribe treatment, or replace professional healthcare advice.
