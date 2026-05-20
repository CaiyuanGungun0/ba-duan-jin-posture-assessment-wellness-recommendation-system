import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { poseApi, sessionsApi } from "../services/api";

// ── Constants ─────────────────────────────────────────────────────────────────

const WS_URL = "ws://localhost:8000/api/pose/stream";
const CAPTURE_INTERVAL_MS = 100; // 10 fps to backend

const CONNECTIONS = [
  [0,1],[1,2],[2,3],[3,7],[0,4],[4,5],[5,6],[6,8],[9,10],
  [11,12],[11,13],[13,15],[15,17],[15,19],[15,21],[17,19],
  [12,14],[14,16],[16,18],[16,20],[16,22],[18,20],
  [11,23],[12,24],[23,24],[23,25],[24,26],
  [25,27],[26,28],[27,29],[28,30],[29,31],[30,32],[27,31],[28,32],
];

// ── Skeleton drawing ──────────────────────────────────────────────────────────

function drawSkeleton(canvas, landmarks, mirrored = false) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!landmarks) return;

  const w = canvas.width, h = canvas.height;
  const MIN_VIS = 0.3;

  const px = (lm) => (mirrored ? 1 - lm.x : lm.x) * w;
  const py = (lm) => lm.y * h;

  ctx.strokeStyle = "#4a7c59";
  ctx.lineWidth = 2;
  for (const [a, b] of CONNECTIONS) {
    const lA = landmarks[a], lB = landmarks[b];
    if (!lA || !lB || lA.visibility < MIN_VIS || lB.visibility < MIN_VIS) continue;
    ctx.beginPath();
    ctx.moveTo(px(lA), py(lA));
    ctx.lineTo(px(lB), py(lB));
    ctx.stroke();
  }
  for (const lm of landmarks) {
    if (lm.visibility < MIN_VIS) continue;
    ctx.beginPath();
    ctx.arc(px(lm), py(lm), 4, 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.strokeStyle = "#4a7c59";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmtTime = (s) =>
  `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

function scoreColor(v) {
  return v >= 80 ? "var(--green-500)" : v >= 60 ? "#c8a830" : "#e05252";
}

// Binary search: find frame index closest to target_ms
function findFrameIdx(frames, targetMs) {
  if (!frames.length) return -1;
  let lo = 0, hi = frames.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].timestamp_ms < targetMs) lo = mid + 1;
    else hi = mid;
  }
  if (lo > 0 && Math.abs(frames[lo - 1].timestamp_ms - targetMs) < Math.abs(frames[lo].timestamp_ms - targetMs))
    return lo - 1;
  return lo;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ModeSelect({ onSelect }) {
  return (
    <div className="page-container" style={{ maxWidth: 640, margin: "0 auto" }}>
      <h2 style={{ marginBottom: 8 }}>Exercise Detection Session</h2>
      <p style={{ color: "var(--text-muted)", marginBottom: 32, fontSize: "0.95rem" }}>
        Choose how you would like to analyse your Ba Duan Jin practice.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Live camera */}
        <button
          onClick={() => onSelect("live")}
          style={{
            background: "var(--beige-100)", border: "2px solid var(--green-300)",
            borderRadius: 14, padding: "32px 24px", cursor: "pointer",
            textAlign: "center", transition: "all 0.2s",
          }}
          onMouseEnter={e => e.currentTarget.style.borderColor = "var(--green-500)"}
          onMouseLeave={e => e.currentTarget.style.borderColor = "var(--green-300)"}
        >
          <div style={{ fontSize: "2.8rem", marginBottom: 14 }}>📷</div>
          <h3 style={{ marginBottom: 8, color: "var(--green-700)" }}>Live Camera Input</h3>
          <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", lineHeight: 1.6 }}>
            Use your webcam for real-time pose detection, live accuracy score,
            rep counting, and instant corrective feedback.
          </p>
        </button>

        {/* Video upload */}
        <button
          onClick={() => onSelect("video")}
          style={{
            background: "var(--beige-100)", border: "2px solid var(--green-300)",
            borderRadius: 14, padding: "32px 24px", cursor: "pointer",
            textAlign: "center", transition: "all 0.2s",
          }}
          onMouseEnter={e => e.currentTarget.style.borderColor = "var(--green-500)"}
          onMouseLeave={e => e.currentTarget.style.borderColor = "var(--green-300)"}
        >
          <div style={{ fontSize: "2.8rem", marginBottom: 14 }}>🎬</div>
          <h3 style={{ marginBottom: 8, color: "var(--green-700)" }}>Upload Exercise Video</h3>
          <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", lineHeight: 1.6 }}>
            Upload a recorded video of your session. The system will analyse
            your form and performance frame-by-frame — then replay with overlays.
          </p>
        </button>
      </div>
    </div>
  );
}

// ── Video Upload + Replay mode ────────────────────────────────────────────────

function VideoMode({ onSaveSession, onBack }) {
  const videoRef  = useRef(null);
  const canvasRef = useRef(null);
  const fileRef   = useRef(null);

  const [step, setStep]         = useState("pick");   // pick | uploading | analyzing | replay
  const [videoFile, setFile]    = useState(null);
  const [videoUrl,  setUrl]     = useState(null);
  const [progress,  setProgress]= useState(0);        // upload progress 0-100
  const [results,   setResults] = useState(null);     // API response
  const [curFrame,  setCurFrame]= useState(null);     // frame shown during replay
  const [saving,    setSaving]  = useState(false);
  const [error,     setError]   = useState(null);

  // Clean up object URL on unmount
  useEffect(() => () => { if (videoUrl) URL.revokeObjectURL(videoUrl); }, [videoUrl]);

  const handleFilePick = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setUrl(URL.createObjectURL(f));
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!videoFile) return;
    setStep("uploading");
    setProgress(0);
    setError(null);
    try {
      setStep("analyzing");
      const res = await poseApi.analyzeVideo(videoFile, (ev) => {
        if (ev.total) setProgress(Math.round((ev.loaded / ev.total) * 100));
      });
      setResults(res.data);
      setStep("replay");
    } catch (err) {
      setError(err.response?.data?.detail || "Analysis failed. Please try a different video.");
      setStep("pick");
    }
  };

  // Sync skeleton overlay to video playback position
  const handleTimeUpdate = useCallback(() => {
    if (!results?.frames || !videoRef.current) return;
    const ms  = videoRef.current.currentTime * 1000;
    const idx = findFrameIdx(results.frames, ms);
    if (idx < 0) return;
    const frame = results.frames[idx];
    setCurFrame(frame);
    if (canvasRef.current) drawSkeleton(canvasRef.current, frame.landmarks, false);
  }, [results]);

  const handleSave = async () => {
    if (!results) return;
    setSaving(true);
    try {
      const scored = results.frames.filter(f => f.accuracy != null);
      const poseScores = scored.map(f => ({
        movement_name: f.action_label || "unknown",
        accuracy: f.accuracy,
      }));
      await onSaveSession({
        duration_seconds: Math.round(results.duration_ms / 1000),
        pose_scores: poseScores,
        notes: "Recorded via video upload analysis",
        session_type: "assessment",
      });
    } finally {
      setSaving(false);
    }
  };

  const summary = results?.summary;

  return (
    <div className="page-container">
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
        <button
          onClick={onBack}
          style={{ background: "none", border: "none", cursor: "pointer",
            color: "var(--text-muted)", fontSize: "0.85rem", padding: 0 }}>
          ← Change method
        </button>
        <h2 style={{ margin: 0 }}>Upload Exercise Video</h2>
      </div>

      {/* PICK step */}
      {step === "pick" && (
        <div style={{ maxWidth: 540 }}>
          <div
            onClick={() => fileRef.current?.click()}
            style={{
              border: "2px dashed var(--green-300)", borderRadius: 12,
              padding: "40px 24px", textAlign: "center", cursor: "pointer",
              background: "var(--beige-50)", transition: "border-color 0.2s",
            }}
            onMouseEnter={e => e.currentTarget.style.borderColor = "var(--green-500)"}
            onMouseLeave={e => e.currentTarget.style.borderColor = "var(--green-300)"}
          >
            <div style={{ fontSize: "2.4rem", marginBottom: 10 }}>🎬</div>
            <p style={{ fontWeight: 600, marginBottom: 4, color: "var(--green-700)" }}>
              Click to select a video file
            </p>
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
              MP4, MOV, AVI, WebM · Max 200 MB
            </p>
            <input
              ref={fileRef} type="file"
              accept="video/mp4,video/quicktime,video/avi,video/webm,.mp4,.mov,.avi,.webm,.mkv"
              style={{ display: "none" }}
              onChange={handleFilePick}
            />
          </div>

          {videoFile && (
            <div style={{ marginTop: 16, padding: "12px 16px",
              background: "var(--beige-100)", borderRadius: 8,
              display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{videoFile.name}</div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  {(videoFile.size / 1024 / 1024).toFixed(1)} MB
                </div>
              </div>
              <button className="btn btn-primary" onClick={handleAnalyze} style={{ minWidth: 140 }}>
                Analyse Video
              </button>
            </div>
          )}

          {error && (
            <div style={{ marginTop: 12, padding: "10px 14px", background: "#fee2e2",
              borderRadius: 8, color: "#b91c1c", fontSize: "0.85rem" }}>
              {error}
            </div>
          )}

          <div className="card" style={{ marginTop: 20 }}>
            <p className="section-title">Tips for best results</p>
            <ul style={{ fontSize: "0.82rem", color: "var(--text-secondary)",
              paddingLeft: 18, lineHeight: 1.9, margin: 0 }}>
              <li>Ensure your full body (head to ankles) is visible throughout</li>
              <li>Good, even lighting with no strong backlight</li>
              <li>Film from the front at 1.5–2 m distance</li>
              <li>Wear fitted clothing so landmarks are detected clearly</li>
            </ul>
          </div>
        </div>
      )}

      {/* UPLOADING / ANALYZING step */}
      {(step === "uploading" || step === "analyzing") && (
        <div style={{ maxWidth: 420, textAlign: "center", paddingTop: 48 }}>
          <div style={{ fontSize: "2.5rem", marginBottom: 16, animation: "spin 1.5s linear infinite" }}>
            ⚙️
          </div>
          <h3 style={{ marginBottom: 8, color: "var(--green-700)" }}>
            {step === "uploading" ? "Uploading…" : "Analysing your video…"}
          </h3>
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: 24 }}>
            {step === "uploading"
              ? `${progress}% uploaded`
              : "Running pose detection frame-by-frame. This may take a moment for longer videos."}
          </p>
          <div style={{ height: 8, background: "#e5e7eb", borderRadius: 4, overflow: "hidden" }}>
            <div style={{
              height: "100%", background: "var(--green-500)", borderRadius: 4,
              width: step === "uploading" ? `${progress}%` : "100%",
              animation: step === "analyzing" ? "indeterminate 1.4s ease infinite" : "none",
              transition: "width 0.3s",
            }} />
          </div>
        </div>
      )}

      {/* REPLAY step */}
      {step === "replay" && results && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 20, alignItems: "start" }}>

          {/* Video + canvas overlay */}
          <div style={{ position: "relative", background: "#000", borderRadius: 12, overflow: "hidden" }}>
            <video
              ref={videoRef}
              src={videoUrl}
              controls
              style={{ width: "100%", display: "block" }}
              onTimeUpdate={handleTimeUpdate}
              onLoadedMetadata={() => {
                if (canvasRef.current && videoRef.current) {
                  canvasRef.current.width  = videoRef.current.videoWidth;
                  canvasRef.current.height = videoRef.current.videoHeight;
                }
              }}
            />
            <canvas
              ref={canvasRef}
              style={{
                position: "absolute", inset: 0,
                width: "100%", height: "100%",
                pointerEvents: "none",
              }}
            />

            {/* Live overlay badges during replay */}
            {curFrame && (
              <>
                <div style={{
                  position: "absolute", top: 10, left: 10,
                  background: curFrame.full_body_detected
                    ? "rgba(0,0,0,0.6)" : "rgba(160,80,0,0.75)",
                  color: "#fff", borderRadius: 8,
                  padding: "5px 12px", fontSize: "0.82rem", fontWeight: 600,
                }}>
                  {curFrame.full_body_detected
                    ? curFrame.accuracy != null
                      ? `${curFrame.accuracy}% accuracy`
                      : "Scoring…"
                    : "Full body not in frame"}
                  {curFrame.full_body_detected && curFrame.action_label &&
                    ` · ${curFrame.action_label}`}
                </div>

                {curFrame.full_body_detected && curFrame.advice?.length > 0 && (
                  <div style={{
                    position: "absolute", bottom: 50, left: 10, right: 10,
                    background: "rgba(0,0,0,0.65)", color: "#fff",
                    borderRadius: 8, padding: "7px 12px",
                    fontSize: "0.82rem", lineHeight: 1.5,
                  }}>
                    {curFrame.advice[0]}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Side panel */}
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

            {/* Summary card */}
            <div className="card">
              <p className="section-title">Session Summary</p>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[
                  ["Duration",     fmtTime(Math.round(summary.duration_ms / 1000))],
                  ["Avg Accuracy", summary.avg_accuracy != null ? `${summary.avg_accuracy}%` : "N/A"],
                  ["Frames Scored",`${summary.scored_frames} / ${summary.total_frames_proc}`],
                  ["Main Movement", summary.dominant_action || "—"],
                ].map(([k, v]) => (
                  <div key={k} style={{ display: "flex", justifyContent: "space-between",
                    fontSize: "0.85rem" }}>
                    <span style={{ color: "var(--text-muted)" }}>{k}</span>
                    <strong style={k === "Avg Accuracy" && summary.avg_accuracy != null
                      ? { color: scoreColor(summary.avg_accuracy) } : {}}>
                      {v}
                    </strong>
                  </div>
                ))}
              </div>

              {/* Score meter */}
              {summary.avg_accuracy != null && (
                <div style={{ marginTop: 14 }}>
                  <div style={{ height: 10, background: "#e5e7eb", borderRadius: 5, overflow: "hidden" }}>
                    <div style={{
                      height: "100%", borderRadius: 5,
                      width: `${summary.avg_accuracy}%`,
                      background: scoreColor(summary.avg_accuracy),
                      transition: "width 0.6s ease",
                    }} />
                  </div>
                </div>
              )}
            </div>

            {/* Movements detected */}
            {summary.actions_detected?.length > 0 && (
              <div className="card">
                <p className="section-title">Movements Detected</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {summary.actions_detected.map((a, i) => (
                    <span key={i} style={{
                      background: "var(--green-50)", color: "var(--green-700)",
                      padding: "3px 10px", borderRadius: 20,
                      fontSize: "0.75rem", fontWeight: 600,
                    }}>{a}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Top advice */}
            {summary.top_advice?.length > 0 && (
              <div className="card">
                <p className="section-title">Key Corrective Advice</p>
                <ul style={{ paddingLeft: 16, margin: 0, fontSize: "0.82rem",
                  color: "var(--text-secondary)", lineHeight: 1.8 }}>
                  {summary.top_advice.map((a, i) => <li key={i}>{a}</li>)}
                </ul>
              </div>
            )}

            {/* Actions */}
            <button
              className="btn btn-primary"
              onClick={handleSave}
              disabled={saving}
              style={{ width: "100%" }}
            >
              {saving ? "Saving…" : "Save as Session"}
            </button>
            <button
              className="btn btn-outline"
              onClick={onBack}
              style={{ width: "100%" }}
            >
              Analyse Another Video
            </button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes indeterminate {
          0%   { transform: translateX(-100%); width: 40%; }
          100% { transform: translateX(350%);  width: 40%; }
        }
      `}</style>
    </div>
  );
}

// ── Live Camera mode (original flow) ─────────────────────────────────────────

function LiveMode({ onSaveSession, onBack }) {
  const videoRef    = useRef(null);
  const canvasRef   = useRef(null);
  const wsRef       = useRef(null);
  const intervalRef = useRef(null);
  const scoresRef   = useRef([]);

  const [status,   setStatus]   = useState("idle");
  const [feedback, setFeedback] = useState({ accuracy: null, advice: [], action_label: null, full_body_detected: false });
  const [elapsed,  setElapsed]  = useState(0);
  const [saving,   setSaving]   = useState(false);
  const startTimeRef = useRef(null);

  useEffect(() => {
    if (status !== "active") return;
    const t = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);
    return () => clearInterval(t);
  }, [status]);

  const startSession = useCallback(async () => {
    setStatus("connecting");
    scoresRef.current = [];
    setElapsed(0);

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true });
    } catch {
      alert("Camera access denied. Please allow camera and try again.");
      setStatus("idle");
      return;
    }
    if (videoRef.current) videoRef.current.srcObject = stream;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("active");
      startTimeRef.current = Date.now();

      intervalRef.current = setInterval(() => {
        if (ws.readyState !== WebSocket.OPEN) return;
        const v = videoRef.current;
        const tmp = document.createElement("canvas");
        tmp.width = 640; tmp.height = 480;
        tmp.getContext("2d").drawImage(v, 0, 0, tmp.width, tmp.height);
        tmp.toBlob((blob) => {
          if (!blob) return;
          const reader = new FileReader();
          reader.onloadend = () => {
            const b64 = reader.result.split(",")[1];
            if (ws.readyState === WebSocket.OPEN) ws.send(b64);
          };
          reader.readAsDataURL(blob);
        }, "image/jpeg", 0.7);
      }, CAPTURE_INTERVAL_MS);
    };

    ws.onmessage = (evt) => {
      const data = JSON.parse(evt.data);
      if (data.error) return;
      setFeedback({
        accuracy:           data.accuracy,
        advice:             data.advice ?? [],
        action_label:       data.action_label,
        full_body_detected: data.full_body_detected ?? false,
      });
      if (canvasRef.current) drawSkeleton(canvasRef.current, data.landmarks, true);
      if (data.full_body_detected && data.accuracy != null) {
        scoresRef.current.push({
          movement_name: data.action_label ?? "unknown",
          accuracy: data.accuracy,
        });
      }
    };

    ws.onclose = () => clearInterval(intervalRef.current);
  }, []);

  const stopSession = useCallback(async () => {
    clearInterval(intervalRef.current);
    wsRef.current?.close();
    if (videoRef.current?.srcObject) {
      videoRef.current.srcObject.getTracks().forEach((t) => t.stop());
    }
    setSaving(true);
    await onSaveSession({
      duration_seconds: elapsed,
      pose_scores: scoresRef.current,
      session_type: "guided",
    });
    setSaving(false);
  }, [elapsed, onSaveSession]);

  return (
    <div className="page-container">
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        {status === "idle" && (
          <button onClick={onBack}
            style={{ background: "none", border: "none", cursor: "pointer",
              color: "var(--text-muted)", fontSize: "0.85rem", padding: 0 }}>
            ← Change method
          </button>
        )}
        <h2 style={{ margin: 0 }}>Live Session</h2>
      </div>

      <div className="session-layout">
        {/* Video panel */}
        <div className="video-panel" ref={(el) => {
          if (el && canvasRef.current) {
            canvasRef.current.width  = el.clientWidth;
            canvasRef.current.height = el.clientHeight;
          }
        }}>
          <video ref={videoRef} autoPlay muted playsInline style={{ transform: "scaleX(-1)" }} />
          <canvas ref={canvasRef} style={{ transform: "scaleX(-1)" }} />

          {status === "active" && (
            <>
              <div className="score-badge" style={{
                background: feedback.full_body_detected
                  ? "rgba(0,0,0,0.55)" : "rgba(180,90,0,0.75)",
              }}>
                {feedback.full_body_detected
                  ? feedback.accuracy != null ? `${feedback.accuracy}% accuracy` : "Scoring…"
                  : "Pose detected…"}
                {feedback.full_body_detected && feedback.action_label && ` · ${feedback.action_label}`}
                <span style={{ marginLeft: 12, fontWeight: 400, opacity: 0.8 }}>
                  {fmtTime(elapsed)}
                </span>
              </div>

              {!feedback.full_body_detected ? (
                <div className="advice-badge" style={{
                  background: "rgba(180,90,0,0.85)",
                  display: "flex", alignItems: "center", gap: 8,
                }}>
                  <span style={{ fontSize: "1.1rem" }}>⚠️</span>
                  <span>
                    Please keep a distance from your device so your full body is visible — this ensures accurate posture estimation.
                  </span>
                </div>
              ) : feedback.advice.length > 0 && (
                <div className="advice-badge">{feedback.advice[0]}</div>
              )}
            </>
          )}

          {status === "idle" && (
            <div style={{
              position: "absolute", inset: 0, display: "flex",
              flexDirection: "column", alignItems: "center", justifyContent: "center",
              color: "#ccc", gap: 12,
            }}>
              <svg width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                <path d="M15 10l4.55-2.27A1 1 0 0121 8.61v6.78a1 1 0 01-1.45.88L15 14M3 8a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <p style={{ fontSize: "0.9rem" }}>Camera preview will appear here</p>
            </div>
          )}
        </div>

        {/* Side panel */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="card">
            <p className="section-title">Session Controls</p>
            {status === "idle" && (
              <button className="btn btn-primary" style={{ width: "100%" }} onClick={startSession}>
                Start Practice
              </button>
            )}
            {status === "connecting" && (
              <button className="btn btn-primary" style={{ width: "100%" }} disabled>Connecting…</button>
            )}
            {status === "active" && (
              <button className="btn btn-danger" style={{ width: "100%" }} onClick={stopSession}
                disabled={saving}>
                {saving ? "Saving…" : "End Session"}
              </button>
            )}
          </div>

          {status === "active" && (
            <div className="card">
              <p className="section-title">Live Feedback</p>
              {!feedback.full_body_detected ? (
                <div style={{
                  background: "#fff3cd", border: "1px solid #f59e0b",
                  borderRadius: 8, padding: "10px 12px",
                  fontSize: "0.82rem", color: "#7c4a00", lineHeight: 1.5,
                }}>
                  <strong>Full body not detected.</strong><br />
                  Keep a distance from your device so your full body — including shoulders,
                  hips, knees, and ankles — is visible to ensure estimation accuracy.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem" }}>
                    <span style={{ color: "var(--text-muted)" }}>Elapsed</span>
                    <strong>{fmtTime(elapsed)}</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem" }}>
                    <span style={{ color: "var(--text-muted)" }}>Frames scored</span>
                    <strong>{scoresRef.current.length}</strong>
                  </div>
                  {feedback.accuracy != null && (
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem" }}>
                      <span style={{ color: "var(--text-muted)" }}>Latest accuracy</span>
                      <strong style={{ color: scoreColor(feedback.accuracy) }}>
                        {feedback.accuracy}%
                      </strong>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="card">
            <p className="section-title">Tips</p>
            <ul style={{ fontSize: "0.85rem", color: "var(--text-secondary)", paddingLeft: 18, lineHeight: 1.8 }}>
              <li>Stand 1.5–2 m from the camera</li>
              <li>Ensure good lighting</li>
              <li>Follow the posture advice overlays</li>
              <li>Breathe slowly and deliberately</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Root Session page ─────────────────────────────────────────────────────────

export default function Session() {
  const navigate = useNavigate();
  const [mode, setMode]               = useState(null); // null | "live" | "video"
  const [savedSession, setSavedSession] = useState(null);
  const [discarding, setDiscarding]   = useState(false);

  const handleSave = useCallback(async (payload) => {
    try {
      const res = await sessionsApi.create(payload);
      setSavedSession(res.data);
    } catch (err) {
      console.error("Failed to save session", err);
      setSavedSession({ total_score: 0, duration_seconds: payload.duration_seconds });
    }
  }, []);

  // Show summary screen after any save
  if (savedSession) {
    const avgScore = savedSession.total_score ?? 0;
    const mins = Math.floor((savedSession.duration_seconds ?? 0) / 60);
    const secs  = (savedSession.duration_seconds ?? 0) % 60;
    const col   = scoreColor(avgScore);

    const discardSession = async () => {
      if (!savedSession.id) { navigate("/"); return; }
      setDiscarding(true);
      try { await sessionsApi.delete(savedSession.id); } catch {}
      navigate("/");
    };

    return (
      <div className="page-container" style={{ textAlign: "center", paddingTop: 72 }}>
        <div style={{ fontSize: "3rem", marginBottom: 12 }}>🎉</div>
        <h2 style={{ color: "var(--green-700)", marginBottom: 6 }}>Session Complete!</h2>
        <p style={{ color: "var(--text-muted)", marginBottom: 24, fontSize: "0.95rem" }}>
          Your progress has been saved successfully.
        </p>
        <div style={{
          display: "inline-flex", gap: 32, background: "var(--beige-100)",
          borderRadius: 14, padding: "16px 32px", marginBottom: 28,
        }}>
          <div>
            <div style={{ fontSize: "1.6rem", fontWeight: 700, color: col }}>
              {avgScore.toFixed(1)}%
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Avg Score</div>
          </div>
          <div>
            <div style={{ fontSize: "1.6rem", fontWeight: 700, color: "var(--green-700)" }}>
              {String(mins).padStart(2, "0")}:{String(secs).padStart(2, "0")}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Duration</div>
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
          <button className="btn btn-primary" style={{ minWidth: 180 }} onClick={() => navigate("/")}>
            View Dashboard
          </button>
          <button
            onClick={discardSession} disabled={discarding}
            style={{
              background: "none", border: "none", cursor: discarding ? "not-allowed" : "pointer",
              fontSize: "0.8rem", color: "var(--text-muted)",
              textDecoration: "underline", textDecorationStyle: "dotted",
              padding: "4px 0", opacity: discarding ? 0.5 : 1,
            }}
          >
            {discarding ? "Discarding…" : "Don't want to save this session? Discard it"}
          </button>
        </div>
      </div>
    );
  }

  if (mode === null)  return <ModeSelect onSelect={setMode} />;
  if (mode === "live") return <LiveMode  onSaveSession={handleSave} onBack={() => setMode(null)} />;
  if (mode === "video") return <VideoMode onSaveSession={handleSave} onBack={() => setMode(null)} />;
  return null;
}
