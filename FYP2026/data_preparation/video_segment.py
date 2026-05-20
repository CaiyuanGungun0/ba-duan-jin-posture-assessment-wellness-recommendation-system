from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
from dataclasses import dataclass
from typing import Protocol
from pathlib import Path

import cv2
try:
    import mediapipe as mp
except ImportError:  # Keep split/frame extraction usable even before MediaPipe is installed.
    mp = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POSE_MODEL = PROJECT_ROOT / "models" / "mediapipe" / "pose_landmarker_full.task"
DEFAULT_VIDEO = PROJECT_ROOT / "data" / "raw_video" / "baduanjin_video01.mp4"
DEFAULT_CLIPS_DIR = PROJECT_ROOT / "data" / "processed_video" / "video01_segments"
DEFAULT_FRAMES_DIR = PROJECT_ROOT / "data" / "frames" / "video01_segments"
DEFAULT_LANDMARKS_CSV = PROJECT_ROOT / "data" / "keypoints" / "video01_segments_landmarks.csv"


@dataclass(frozen=True)
class Segment:
    action: int
    rep: int
    start: str
    end: str

    @property
    def label(self) -> str:
        return f"action{self.action:02d}_rep{self.rep:02d}"


SEGMENTS: tuple[Segment, ...] = (
    Segment(1, 1, "0:00:36", "0:00:54"),
    Segment(1, 2, "0:01:11", "0:01:27"),
    Segment(1, 3, "0:01:27", "0:01:45"),
    Segment(2, 1, "0:02:15", "0:02:44"),
    Segment(2, 2, "0:02:45", "0:03:15"),
    Segment(2, 3, "0:03:15", "0:03:45"),
    Segment(3, 1, "0:04:30", "0:04:53"),
    Segment(3, 2, "0:04:06", "0:04:29"),
    Segment(3, 3, "0:03:45", "0:04:04"),
    Segment(4, 1, "0:04:56", "0:05:19"),
    Segment(4, 2, "0:05:20", "0:05:43"),
    Segment(4, 3, "0:05:43", "0:06:05"),
    Segment(5, 1, "0:06:18", "0:06:43"),
    Segment(5, 2, "0:06:44", "0:07:09"),
    Segment(5, 3, "0:07:10", "0:07:35"),
    Segment(6, 1, "0:07:50", "0:08:13"),
    Segment(6, 2, "0:08:13", "0:08:31"),
    Segment(6, 3, "0:08:31", "0:08:51"),
    Segment(6, 4, "0:09:29", "0:09:49"),
    Segment(7, 1, "0:09:56", "0:10:13"),
    Segment(7, 2, "0:10:13", "0:10:30"),
    Segment(7, 3, "0:10:31", "0:10:46"),
    Segment(8, 1, "0:10:55", "0:10:59"),
    Segment(8, 2, "0:11:05", "0:11:10"),
    Segment(8, 3, "0:11:35", "0:11:39"),
)


class PoseBackend(Protocol):
    def detect(self, rgb_frame):
        pass

    def close(self) -> None:
        pass


class TasksPoseBackend:
    def __init__(self, model_path: Path, min_detection_confidence: float) -> None:
        if mp is None:
            raise RuntimeError("MediaPipe is not installed. Install it with: pip install mediapipe")
        if not model_path.exists():
            raise FileNotFoundError(f"MediaPipe Tasks pose model not found: {model_path}")

        from mediapipe.tasks.python.core.base_options import BaseOptions
        from mediapipe.tasks.python.vision import pose_landmarker
        from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

        options = pose_landmarker.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=VisionTaskRunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=min_detection_confidence,
            min_pose_presence_confidence=min_detection_confidence,
            output_segmentation_masks=False,
        )
        self._landmarker = pose_landmarker.PoseLandmarker.create_from_options(options)

    def detect(self, rgb_frame) -> list[float] | None:
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._landmarker.detect(image)
        if not result.pose_landmarks:
            return None

        features: list[float] = []
        for landmark in result.pose_landmarks[0]:
            features.extend(
                [
                    landmark.x if landmark.x is not None else "",
                    landmark.y if landmark.y is not None else "",
                    landmark.z if landmark.z is not None else "",
                    landmark.visibility if landmark.visibility is not None else "",
                ]
            )
        return features

    def close(self) -> None:
        self._landmarker.close()


def landmark_columns() -> list[str]:
    columns: list[str] = []
    for landmark_idx in range(33):
        columns.extend(
            [
                f"lm_{landmark_idx}_x",
                f"lm_{landmark_idx}_y",
                f"lm_{landmark_idx}_z",
                f"lm_{landmark_idx}_visibility",
            ]
        )
    return columns


def create_pose_backend(
    pose_model: Path,
    min_detection_confidence: float,
) -> PoseBackend:
    return TasksPoseBackend(model_path=pose_model, min_detection_confidence=min_detection_confidence)


def resolve_executable(executable: str) -> str | None:
    resolved = shutil.which(executable)
    if resolved is not None:
        return resolved
    executable_path = Path(executable)
    if executable_path.exists():
        return str(executable_path)
    return None


def split_video(
    input_video: Path,
    clips_dir: Path,
    ffmpeg_bin: str = "ffmpeg",
    overwrite: bool = False,
) -> list[tuple[Segment, Path]]:
    ffmpeg = resolve_executable(ffmpeg_bin)
    if ffmpeg is None:
        raise RuntimeError("FFmpeg was not found. Install FFmpeg or pass --ffmpeg-bin with the executable path.")
    if not input_video.exists():
        raise FileNotFoundError(f"Input video not found: {input_video}")

    clips_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[tuple[Segment, Path]] = []

    for segment in SEGMENTS:
        action_dir = clips_dir / f"action{segment.action:02d}"
        action_dir.mkdir(parents=True, exist_ok=True)
        output_clip = action_dir / f"{segment.label}.mp4"
        outputs.append((segment, output_clip))

        if output_clip.exists() and not overwrite:
            print(f"Clip exists, skipping: {output_clip}")
            continue

        command = [
            ffmpeg,
            "-y" if overwrite else "-n",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            segment.start,
            "-to",
            segment.end,
            "-i",
            str(input_video),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output_clip),
        ]
        subprocess.run(command, check=True)
        print(f"Created clip: {output_clip}")

    return outputs


def extract_frames(
    clips: list[tuple[Segment, Path]],
    frames_dir: Path,
    target_fps: float = 15.0,
    overwrite: bool = False,
) -> list[tuple[Segment, Path, list[Path]]]:
    if target_fps <= 0:
        raise ValueError("target_fps must be greater than 0.")

    frames_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[tuple[Segment, Path, list[Path]]] = []

    for segment, clip_path in clips:
        if not clip_path.exists():
            raise FileNotFoundError(f"Clip not found: {clip_path}")

        segment_frames_dir = frames_dir / f"action{segment.action:02d}" / segment.label
        segment_frames_dir.mkdir(parents=True, exist_ok=True)
        existing_frames = sorted(segment_frames_dir.glob("*.jpg"))
        if existing_frames and not overwrite:
            print(f"Frames exist, skipping: {segment_frames_dir}")
            outputs.append((segment, segment_frames_dir, existing_frames))
            continue

        if overwrite:
            for old_frame in existing_frames:
                old_frame.unlink()

        cap = cv2.VideoCapture(str(clip_path))
        if not cap.isOpened():
            raise RuntimeError(f"Could not open clip: {clip_path}")

        source_fps = cap.get(cv2.CAP_PROP_FPS)
        if source_fps <= 0:
            source_fps = target_fps
        frame_step = max(1, round(source_fps / target_fps))

        saved_frames: list[Path] = []
        frame_index = 0
        saved_index = 0

        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_index % frame_step == 0:
                output_frame = segment_frames_dir / f"{segment.label}_frame{saved_index:05d}.jpg"
                cv2.imwrite(str(output_frame), frame)
                saved_frames.append(output_frame)
                saved_index += 1
            frame_index += 1

        cap.release()
        print(f"Extracted {len(saved_frames)} frames from {clip_path.name}")
        outputs.append((segment, segment_frames_dir, saved_frames))

    return outputs


def extract_landmarks(
    frame_sets: list[tuple[Segment, Path, list[Path]]],
    output_csv: Path,
    pose_model: Path = DEFAULT_POSE_MODEL,
    min_detection_confidence: float = 0.5,
) -> int:
    detector = create_pose_backend(
        pose_model=pose_model,
        min_detection_confidence=min_detection_confidence,
    )
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "action",
        "rep",
        "segment",
        "frame_index",
        "frame_path",
        "pose_detected",
        *landmark_columns(),
    ]

    rows_written = 0
    with output_csv.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)

        try:
            for segment, _segment_frames_dir, frame_paths in frame_sets:
                for frame_index, frame_path in enumerate(frame_paths):
                    frame = cv2.imread(str(frame_path))
                    if frame is None:
                        print(f"Could not read frame, skipping: {frame_path}")
                        continue

                    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    features = detector.detect(image)
                    values: list[float | str | int | bool] = [
                        segment.action,
                        segment.rep,
                        segment.label,
                        frame_index,
                        str(frame_path),
                    ]

                    if features:
                        values.extend([True, *features])
                    else:
                        values.extend([False, *([""] * 132)])

                    writer.writerow(values)
                    rows_written += 1

                print(f"Extracted landmarks for {segment.label}: {len(frame_paths)} frames")
        finally:
            detector.close()

    print(f"Saved {rows_written} landmark rows to {output_csv}")
    return rows_written


def _ts_to_ms(timestamp: str) -> int:
    """Convert 'H:MM:SS' or 'H:MM:SS.mmm' to integer milliseconds."""
    parts = timestamp.split(":")
    hours, minutes, seconds = int(parts[0]), int(parts[1]), float(parts[2])
    return int((hours * 3600 + minutes * 60 + seconds) * 1000)


def extract_frames_direct(
    input_video: Path,
    frames_dir: Path,
    target_fps: float = 15.0,
    overwrite: bool = False,
) -> list[tuple[Segment, Path, list[Path]]]:
    """Extract frames directly from the source video by time-seeking — no FFmpeg needed."""
    if not input_video.exists():
        raise FileNotFoundError(f"Input video not found: {input_video}")

    cap = cv2.VideoCapture(str(input_video))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {input_video}")

    frame_interval_ms = 1000.0 / target_fps
    outputs: list[tuple[Segment, Path, list[Path]]] = []

    try:
        for segment in SEGMENTS:
            segment_frames_dir = frames_dir / f"action{segment.action:02d}" / segment.label
            existing = sorted(segment_frames_dir.glob("*.jpg"))
            if existing and not overwrite:
                print(f"Frames exist, skipping: {segment_frames_dir}")
                outputs.append((segment, segment_frames_dir, existing))
                continue

            if overwrite:
                for f in existing:
                    f.unlink()
            segment_frames_dir.mkdir(parents=True, exist_ok=True)

            start_ms = _ts_to_ms(segment.start)
            end_ms = _ts_to_ms(segment.end)
            cap.set(cv2.CAP_PROP_POS_MSEC, start_ms)

            saved_frames: list[Path] = []
            next_capture_ms = float(start_ms)

            while True:
                current_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                if current_ms > end_ms:
                    break
                ok, frame = cap.read()
                if not ok:
                    break
                if cap.get(cv2.CAP_PROP_POS_MSEC) > end_ms:
                    break
                if current_ms >= next_capture_ms:
                    idx = len(saved_frames)
                    out_path = segment_frames_dir / f"{segment.label}_frame{idx:05d}.jpg"
                    cv2.imwrite(str(out_path), frame)
                    saved_frames.append(out_path)
                    next_capture_ms += frame_interval_ms

            print(f"Extracted {len(saved_frames)} frames for {segment.label}")
            outputs.append((segment, segment_frames_dir, saved_frames))
    finally:
        cap.release()

    return outputs


def run_pipeline(
    input_video: Path,
    clips_dir: Path,
    frames_dir: Path,
    landmarks_csv: Path,
    frame_fps: float,
    ffmpeg_bin: str,
    pose_model: Path,
    overwrite: bool,
) -> None:
    ffmpeg = resolve_executable(ffmpeg_bin)
    if ffmpeg is not None:
        clips = split_video(input_video=input_video, clips_dir=clips_dir, ffmpeg_bin=ffmpeg_bin, overwrite=overwrite)
        frame_sets = extract_frames(clips=clips, frames_dir=frames_dir, target_fps=frame_fps, overwrite=overwrite)
    else:
        print("FFmpeg not found — extracting frames directly from source video with OpenCV.")
        frame_sets = extract_frames_direct(
            input_video=input_video,
            frames_dir=frames_dir,
            target_fps=frame_fps,
            overwrite=overwrite,
        )
    extract_landmarks(
        frame_sets=frame_sets,
        output_csv=landmarks_csv,
        pose_model=pose_model,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Split baduanjin_video01.mp4 into Ba-Duan-Jin repetition clips, "
            "sample frames, and extract MediaPipe pose landmarks."
        )
    )
    parser.add_argument("--input-video", type=Path, default=DEFAULT_VIDEO)
    parser.add_argument("--clips-dir", type=Path, default=DEFAULT_CLIPS_DIR)
    parser.add_argument("--frames-dir", type=Path, default=DEFAULT_FRAMES_DIR)
    parser.add_argument("--landmarks-csv", type=Path, default=DEFAULT_LANDMARKS_CSV)
    parser.add_argument("--frame-fps", type=float, default=15.0, help="Frame extraction FPS; use 10-20.")
    parser.add_argument("--ffmpeg-bin", default="ffmpeg", help="FFmpeg executable name or full path.")
    parser.add_argument("--pose-model", type=Path, default=DEFAULT_POSE_MODEL, help="MediaPipe Tasks .task model path.")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate clips and frames if they exist.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(
        input_video=args.input_video,
        clips_dir=args.clips_dir,
        frames_dir=args.frames_dir,
        landmarks_csv=args.landmarks_csv,
        frame_fps=args.frame_fps,
        ffmpeg_bin=args.ffmpeg_bin,
        pose_model=args.pose_model,
        overwrite=args.overwrite,
    )
