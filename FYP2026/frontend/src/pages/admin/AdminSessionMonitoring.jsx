import { useEffect, useState } from "react";
import { adminApi } from "../../services/api.js";

const S = {
  card: { background: "#1e293b", borderRadius: 10, padding: 20, marginBottom: 16,
    border: "1px solid #334155" },
  th: { padding: "10px 14px", textAlign: "left", fontSize: "0.75rem",
    color: "#94a3b8", fontWeight: 600, textTransform: "uppercase",
    borderBottom: "1px solid #334155" },
  td: { padding: "12px 14px", fontSize: "0.875rem", borderBottom: "1px solid #1e293b" },
  badge: (color) => ({
    display: "inline-block", padding: "2px 10px", borderRadius: 20,
    fontSize: "0.72rem", fontWeight: 600, background: color + "22", color,
  }),
  btn: (color = "#3b82f6") => ({
    padding: "5px 12px", borderRadius: 6, border: "none", cursor: "pointer",
    fontSize: "0.78rem", background: color + "22", color, fontWeight: 600,
  }),
  input: {
    background: "#0f172a", border: "1px solid #334155", borderRadius: 6,
    color: "#f1f5f9", padding: "8px 12px", fontSize: "0.875rem",
  },
};

function ScoreBar({ value }) {
  const color = value >= 80 ? "#22c55e" : value >= 60 ? "#f59e0b" : "#ef4444";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 6, background: "#0f172a", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${value}%`, height: "100%", background: color, borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: "0.78rem", color, minWidth: 36 }}>{value.toFixed(1)}%</span>
    </div>
  );
}

function SessionDetail({ session, onClose }) {
  return (
    <div style={{
      position: "fixed", inset: 0, background: "#0008", zIndex: 100,
      display: "flex", alignItems: "center", justifyContent: "center",
    }} onClick={onClose}>
      <div style={{ background: "#1e293b", borderRadius: 12, padding: 28, maxWidth: 700,
        width: "90%", maxHeight: "80vh", overflowY: "auto", border: "1px solid #334155" }}
        onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
          <h3 style={{ color: "#f1f5f9" }}>
            Session #{session.id} — {session.username}
          </h3>
          <button onClick={onClose} style={{ background: "none", border: "none",
            color: "#94a3b8", cursor: "pointer", fontSize: "1.2rem" }}>✕</button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 20 }}>
          {[
            ["Date", new Date(session.date).toLocaleString()],
            ["Duration", `${Math.round(session.duration_seconds / 60)} min`],
            ["Type", session.session_type],
            ["Score", `${session.total_score.toFixed(1)}%`],
            ["Movements", session.movement_count],
            ["Calories", `${session.calories_burned.toFixed(0)} kcal`],
          ].map(([k, v]) => (
            <div key={k} style={{ background: "#0f172a", borderRadius: 8, padding: "10px 14px" }}>
              <div style={{ fontSize: "0.72rem", color: "#64748b", marginBottom: 2 }}>{k}</div>
              <div style={{ color: "#f1f5f9", fontWeight: 600 }}>{v}</div>
            </div>
          ))}
        </div>

        {session.session_actions?.length > 0 && (
          <>
            <h4 style={{ color: "#94a3b8", marginBottom: 10 }}>Per-Movement Breakdown</h4>
            {session.session_actions.map(a => (
              <div key={a.id} style={{ background: "#0f172a", borderRadius: 8, padding: 14,
                marginBottom: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{ fontWeight: 600, color: "#f1f5f9" }}>
                    {a.action_no}. {a.action_name}
                  </span>
                  <span style={{ fontSize: "0.78rem", color: "#94a3b8" }}>
                    {a.rep_count} reps
                  </span>
                </div>
                <ScoreBar value={a.avg_score} />
                {a.advice_summary && (() => {
                  try {
                    const tips = JSON.parse(a.advice_summary);
                    return tips.length > 0 ? (
                      <ul style={{ margin: "8px 0 0 16px", color: "#94a3b8", fontSize: "0.78rem" }}>
                        {tips.slice(0, 2).map((t, i) => <li key={i}>{t}</li>)}
                      </ul>
                    ) : null;
                  } catch { return null; }
                })()}
              </div>
            ))}
          </>
        )}

        {session.pose_scores?.length > 0 && (
          <>
            <h4 style={{ color: "#94a3b8", margin: "16px 0 10px" }}>Pose Score Log</h4>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {session.pose_scores.map(p => (
                <span key={p.id} style={{
                  background: "#0f172a", borderRadius: 6, padding: "4px 10px",
                  fontSize: "0.75rem", color: "#94a3b8",
                }}>
                  {p.movement_name}: <strong style={{ color: "#f1f5f9" }}>{p.accuracy.toFixed(0)}%</strong>
                </span>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function AdminSessionMonitoring() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [userId, setUserId] = useState("");

  const load = async (uid = "") => {
    setLoading(true);
    try {
      const params = { limit: 100 };
      if (uid) params.user_id = uid;
      const r = await adminApi.listSessions(params);
      setSessions(r.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openDetail = async (id) => {
    setDetailLoading(true);
    try {
      const r = await adminApi.getSession(id);
      setDetail(r.data);
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <div>
      {detail && <SessionDetail session={detail} onClose={() => setDetail(null)} />}

      <h2 style={{ marginBottom: 8, color: "#f1f5f9" }}>Session Monitoring</h2>
      <p style={{ color: "#94a3b8", marginBottom: 24, fontSize: "0.875rem" }}>
        View all recorded sessions across all users. Click a row to inspect posture results.
      </p>

      <div style={S.card}>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input
            style={{ ...S.input, width: 160 }}
            type="number"
            placeholder="Filter by user ID…"
            value={userId}
            onChange={e => setUserId(e.target.value)}
          />
          <button onClick={() => load(userId)} style={{ ...S.btn(), padding: "8px 18px" }}>
            Filter
          </button>
          <button onClick={() => { setUserId(""); load(""); }}
            style={{ ...S.btn("#94a3b8"), padding: "8px 18px" }}>
            Clear
          </button>
          <span style={{ color: "#64748b", fontSize: "0.8rem", marginLeft: "auto" }}>
            {sessions.length} session(s)
          </span>
        </div>
      </div>

      <div style={{ ...S.card, padding: 0, overflow: "auto" }}>
        {loading ? (
          <div style={{ padding: 24, textAlign: "center", color: "#94a3b8" }}>Loading…</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#0f172a" }}>
                {["ID", "User", "Date", "Duration", "Type", "Score", "Movements",
                  "Calories", "Status", ""].map(h => (
                  <th key={h} style={S.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sessions.length === 0 ? (
                <tr><td colSpan={10} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>
                  No sessions found
                </td></tr>
              ) : sessions.map(s => (
                <tr key={s.id} style={{ cursor: "pointer" }}
                  onMouseEnter={e => e.currentTarget.style.background = "#ffffff08"}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                  <td style={S.td}>{s.id}</td>
                  <td style={S.td}><strong>{s.username}</strong></td>
                  <td style={{ ...S.td, fontSize: "0.78rem", color: "#94a3b8" }}>
                    {new Date(s.date).toLocaleString()}
                  </td>
                  <td style={S.td}>{Math.round(s.duration_seconds / 60)}m</td>
                  <td style={S.td}>
                    <span style={S.badge("#60a5fa")}>{s.session_type}</span>
                  </td>
                  <td style={S.td}>
                    <span style={{
                      color: s.total_score >= 80 ? "#22c55e" : s.total_score >= 60 ? "#f59e0b" : "#ef4444",
                      fontWeight: 600,
                    }}>{s.total_score.toFixed(1)}%</span>
                  </td>
                  <td style={S.td}>{s.movement_count}</td>
                  <td style={S.td}>{s.calories_burned.toFixed(0)}</td>
                  <td style={S.td}>
                    <span style={S.badge(s.completed ? "#22c55e" : "#f59e0b")}>
                      {s.completed ? "Done" : "Partial"}
                    </span>
                  </td>
                  <td style={S.td}>
                    <button onClick={() => openDetail(s.id)} disabled={detailLoading}
                      style={S.btn()}>
                      {detailLoading ? "…" : "Inspect"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
