from __future__ import annotations

import base64
import json
import logging
import os
import tempfile
from collections import Counter, deque
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode
from sqlalchemy.orm import Session

from backend import models
from backend.auth import get_current_user
from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MP_MODEL = PROJECT_ROOT / "models" / "mediapipe" / "pose_landmarker_full.task"
DEFAULT_ACTION_MODEL = PROJECT_ROOT / "models" / "comparison" / "cnn_model.keras"
DEFAULT_KEYPOINTS = PROJECT_ROOT / "data" / "keypoints" / "video01_keypoints.csv"
PER_ACTION_KEYPOINTS_DIR = PROJECT_ROOT / "data" / "keypoints" / "per_action"

# Action labels produced by the CNN → per-action reference keypoint file
_ACTION_LABELS = [f"action{i:02d}" for i in range(1, 9)]


def _load_per_action_refs() -> dict[str, "np.ndarray"]:
    """Load per-action reference keypoints into a dict keyed by action label."""
    try:
        from pose_module.posture_score import load_reference_keypoints
    except ImportError:
        return {}
    refs: dict[str, np.ndarray] = {}
    for label in _ACTION_LABELS:
        path = PER_ACTION_KEYPOINTS_DIR / f"{label}_keypoints.csv"
        if path.exists():
            try:
                refs[label] = load_reference_keypoints(str(path))
            except Exception:
                logger.warning("Could not load reference for %s", label)
    return refs

_MIN_VIS = 0.3

# Landmark indices that must all be visible for a "full body" reading.
# Covers: both shoulders (11,12), both hips (23,24), both knees (25,26), both ankles (27,28).
_FULL_BODY_INDICES = [11, 12, 23, 24, 25, 26, 27, 28]


def _landmarks_to_list(landmarks) -> list[dict]:
    return [
        {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility or 0.0}
        for lm in landmarks
    ]


def _is_full_body(landmarks) -> bool:
    """Return True only when all key body landmarks are confidently visible."""
    return all(
        (landmarks[i].visibility or 0.0) >= _MIN_VIS
        for i in _FULL_BODY_INDICES
    )


@router.websocket("/stream")
async def pose_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time pose feedback.

    Protocol:
      Client → sends base64-encoded JPEG frames as text messages.
      Server → replies with JSON: PoseFrameResult schema.
    """
    await websocket.accept()

    try:
        from pose_module.posture_score import (
            compare_pose, landmarks_to_array, load_reference_keypoints,
        )
        from pose_module.pose_model import PredictionSmoother, load_action_model
    except Exception as exc:
        await websocket.send_text(json.dumps({"error": f"pose_module unavailable: {exc}"}))
        await websocket.close()
        return

    per_action_refs = _load_per_action_refs()
    # Fallback: full-video keypoints if per-action files are missing
    fallback_ref = None
    if not per_action_refs and DEFAULT_KEYPOINTS.exists():
        try:
            fallback_ref = load_reference_keypoints(str(DEFAULT_KEYPOINTS))
        except Exception:
            logger.warning("Could not load reference keypoints — accuracy scoring disabled.")

    action_model = None
    smoother = PredictionSmoother(threshold=0.70, window=7)
    landmark_buffer: deque[np.ndarray] = deque(maxlen=30)

    if DEFAULT_ACTION_MODEL.exists():
        try:
            action_model = load_action_model(DEFAULT_ACTION_MODEL)
            landmark_buffer = deque(maxlen=action_model.sequence_length)
        except Exception:
            logger.warning("Action model unavailable — classification disabled.")

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(DEFAULT_MP_MODEL)),
        running_mode=VisionTaskRunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        output_segmentation_masks=False,
    )

    # Per-action reference frame counters (reset when action changes)
    action_ref_counters: dict[str, int] = {label: 0 for label in _ACTION_LABELS}
    last_action_label: str | None = None

    try:
        with PoseLandmarker.create_from_options(options) as landmarker:
            while True:
                raw = await websocket.receive_text()
                # Expect base64-encoded JPEG
                img_bytes = base64.b64decode(raw)
                np_arr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = landmarker.detect(mp_img)

                payload: dict = {
                    "accuracy": None,
                    "action_label": None,
                    "action_confidence": 0.0,
                    "advice": [],
                    "landmarks": None,
                    "full_body_detected": False,
                }

                if result.pose_landmarks:
                    lm_list = result.pose_landmarks[0]
                    payload["landmarks"] = _landmarks_to_list(lm_list)
                    user_pose = landmarks_to_array(lm_list)

                    full_body = _is_full_body(lm_list)
                    payload["full_body_detected"] = full_body

                    if full_body:
                        # Run action classification first so we know which ref to use
                        detected_action: str | None = None
                        if action_model is not None:
                            landmark_buffer.append(user_pose)
                            if len(landmark_buffer) == landmark_buffer.maxlen:
                                window = np.stack(list(landmark_buffer))
                                raw_pred = action_model.predict_window(window)
                                smoothed = smoother.update(raw_pred)
                                payload["action_label"] = smoothed.label
                                payload["action_confidence"] = smoothed.confidence
                                detected_action = smoothed.label

                        # Reset counter when action changes to re-sync reference
                        if detected_action != last_action_label:
                            if detected_action:
                                action_ref_counters[detected_action] = 0
                            last_action_label = detected_action

                        # Score against action-specific reference frames
                        ref_pool = (
                            per_action_refs.get(detected_action)
                            if detected_action and detected_action in per_action_refs
                            else fallback_ref
                        )
                        if ref_pool is not None:
                            key = detected_action or "__fallback__"
                            idx = action_ref_counters.get(key, 0)
                            ref_frame = ref_pool[idx % len(ref_pool)]
                            score = compare_pose(user_pose, ref_frame, tolerance=1.2)
                            payload["accuracy"] = round(score.accuracy, 1)
                            payload["advice"] = score.advice
                            action_ref_counters[key] = idx + 1

                    else:
                        # Partial body visible — keep landmark overlay but skip scoring
                        smoother.reset()
                        landmark_buffer.clear()
                else:
                    smoother.reset()
                    landmark_buffer.clear()

                await websocket.send_text(json.dumps(payload))

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("Pose stream error: %s", exc)
        try:
            await websocket.send_text(json.dumps({"error": str(exc)}))
        except Exception:
            pass


# ── Video file analysis ───────────────────────────────────────────────────────

_TARGET_ANALYSIS_FPS = 5          # process this many frames per second of video
_MAX_VIDEO_BYTES     = 200 * 1024 * 1024   # 200 MB upload limit


@router.post("/analyze-video")
async def analyze_video(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accept an uploaded exercise video, run MediaPipe + CNN pose analysis on it
    at ~5 fps, and return per-frame results suitable for replay + session saving.
    """
    # ── Validate file type ────────────────────────────────────────────────────
    allowed = {"video/mp4", "video/avi", "video/quicktime", "video/webm",
               "video/x-msvideo", "video/x-matroska"}
    content_type = file.content_type or ""
    suffix = Path(file.filename or "video.mp4").suffix.lower()
    if content_type not in allowed and suffix not in {".mp4", ".avi", ".mov", ".webm", ".mkv"}:
        raise HTTPException(status_code=400, detail="Unsupported video format.")

    # ── Read upload into a temp file ──────────────────────────────────────────
    raw = await file.read()
    if len(raw) > _MAX_VIDEO_BYTES:
        raise HTTPException(status_code=413, detail="Video exceeds 200 MB limit.")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix or ".mp4") as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        # ── Load pose modules ─────────────────────────────────────────────────
        try:
            from pose_module.posture_score import (
                compare_pose, landmarks_to_array, load_reference_keypoints,
            )
            from pose_module.pose_model import PredictionSmoother, load_action_model
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"pose_module unavailable: {exc}")

        per_action_refs_v = _load_per_action_refs()
        fallback_ref_v = None
        if not per_action_refs_v and DEFAULT_KEYPOINTS.exists():
            try:
                fallback_ref_v = load_reference_keypoints(str(DEFAULT_KEYPOINTS))
            except Exception:
                logger.warning("Reference keypoints unavailable — accuracy scoring disabled.")

        action_model = None
        seq_len = 30
        if DEFAULT_ACTION_MODEL.exists():
            try:
                action_model = load_action_model(DEFAULT_ACTION_MODEL)
                seq_len = action_model.sequence_length
            except Exception:
                logger.warning("Action model unavailable — classification disabled.")

        smoother   = PredictionSmoother(threshold=0.70, window=7)
        lm_buffer: deque[np.ndarray] = deque(maxlen=seq_len)
        v_action_ref_counters: dict[str, int] = {label: 0 for label in _ACTION_LABELS}
        v_last_action: str | None = None

        # ── Open video ────────────────────────────────────────────────────────
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise HTTPException(status_code=422, detail="Could not open video file.")

        video_fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_ms  = int((total_frames / video_fps) * 1000)
        step         = max(1, round(video_fps / _TARGET_ANALYSIS_FPS))

        mp_options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(DEFAULT_MP_MODEL)),
            running_mode=VisionTaskRunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            output_segmentation_masks=False,
        )

        frame_results: list[dict] = []
        frame_no      = 0

        with PoseLandmarker.create_from_options(mp_options) as landmarker:
            while True:
                ok, bgr = cap.read()
                if not ok:
                    break

                if frame_no % step != 0:
                    frame_no += 1
                    continue

                timestamp_ms = int((frame_no / video_fps) * 1000)
                rgb    = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = landmarker.detect(mp_img)

                entry: dict = {
                    "timestamp_ms":       timestamp_ms,
                    "accuracy":           None,
                    "full_body_detected": False,
                    "action_label":       None,
                    "action_confidence":  0.0,
                    "advice":             [],
                    "landmarks":          None,
                }

                if result.pose_landmarks:
                    lm_list = result.pose_landmarks[0]
                    entry["landmarks"] = _landmarks_to_list(lm_list)
                    user_pose = landmarks_to_array(lm_list)

                    full_body = _is_full_body(lm_list)
                    entry["full_body_detected"] = full_body

                    if full_body:
                        # Classify action first, then pick matching reference
                        detected_v: str | None = None
                        if action_model is not None:
                            lm_buffer.append(user_pose)
                            if len(lm_buffer) == lm_buffer.maxlen:
                                window   = np.stack(list(lm_buffer))
                                raw_pred = action_model.predict_window(window)
                                smoothed = smoother.update(raw_pred)
                                entry["action_label"]      = smoothed.label
                                entry["action_confidence"] = smoothed.confidence
                                detected_v = smoothed.label

                        if detected_v != v_last_action:
                            if detected_v:
                                v_action_ref_counters[detected_v] = 0
                            v_last_action = detected_v

                        ref_pool_v = (
                            per_action_refs_v.get(detected_v)
                            if detected_v and detected_v in per_action_refs_v
                            else fallback_ref_v
                        )
                        if ref_pool_v is not None:
                            key_v = detected_v or "__fallback__"
                            idx_v = v_action_ref_counters.get(key_v, 0)
                            score = compare_pose(user_pose, ref_pool_v[idx_v % len(ref_pool_v)], tolerance=1.2)
                            entry["accuracy"] = round(score.accuracy, 1)
                            entry["advice"]   = score.advice
                            v_action_ref_counters[key_v] = idx_v + 1
                    else:
                        smoother.reset()
                        lm_buffer.clear()
                else:
                    smoother.reset()
                    lm_buffer.clear()

                frame_results.append(entry)
                frame_no += 1

        cap.release()

        # ── Build summary ─────────────────────────────────────────────────────
        scored = [f for f in frame_results if f["accuracy"] is not None]
        avg_accuracy = round(sum(f["accuracy"] for f in scored) / len(scored), 1) if scored else 0.0

        action_counts: Counter = Counter(
            f["action_label"] for f in frame_results if f["action_label"]
        )
        dominant_action = action_counts.most_common(1)[0][0] if action_counts else None

        advice_flat = [a for f in frame_results for a in f["advice"]]
        advice_counts: Counter = Counter(advice_flat)
        top_advice = [a for a, _ in advice_counts.most_common(3)]

        summary = {
            "avg_accuracy":      avg_accuracy,
            "dominant_action":   dominant_action,
            "actions_detected":  list(action_counts.keys()),
            "top_advice":        top_advice,
            "scored_frames":     len(scored),
            "total_frames_proc": len(frame_results),
            "duration_ms":       duration_ms,
        }

        return {
            "duration_ms":   duration_ms,
            "video_fps":     round(video_fps, 2),
            "summary":       summary,
            "frames":        frame_results,
        }

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
