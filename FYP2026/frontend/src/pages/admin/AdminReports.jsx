import { useEffect, useState } from "react";
import { adminApi } from "../../services/api.js";

const S = {
  card: { background: "#1e293b", borderRadius: 10, padding: 20, marginBottom: 16,
    border: "1px solid #334155" },
  stat: {
    background: "#0f172a", borderRadius: 8, padding: "16px 20px",
    textAlign: "center",
  },
  tab: (active) => ({
    padding: "8px 18px", borderRadius: 6, border: "none", cursor: "pointer",
    fontSize: "0.875rem", fontWeight: active ? 600 : 400,
    background: active ? "#3b82f620" : "transparent",
    color: active ? "#60a5fa" : "#94a3b8",
  }),
  th: { padding: "10px 14px", textAlign: "left", fontSize: "0.75rem",
    color: "#94a3b8", fontWeight: 600, textTransform: "uppercase",
    borderBottom: "1px solid #334155" },
  td: { padding: "10px 14px", fontSize: "0.875rem", borderBottom: "1px solid #1e293b" },
};

function ScoreBar({ value, max = 100 }) {
  const pct = Math.min((value / max) * 100, 100);
  const color = pct >= 70 ? "#22c55e" : pct >= 45 ? "#f59e0b" : "#ef4444";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 8, background: "#0f172a", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 4 }} />
      </div>
      <span style={{ color, fontSize: "0.78rem", minWidth: 40 }}>{value.toFixed(1)}%</span>
    </div>
  );
}

export default function AdminReports() {
  const [tab, setTab] = useState("usage");
  const [usage, setUsage] = useState(null);
  const [accuracy, setAccuracy] = useState(null);
  const [modelEval, setModelEval] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        if (tab === "usage" && !usage) {
          const r = await adminApi.stats();
          setUsage(r.data);
        } else if (tab === "accuracy" && !accuracy) {
          const r = await adminApi.accuracy();
          setAccuracy(r.data);
        } else if (tab === "model" && !modelEval) {
          const r = await adminApi.modelEval();
          setModelEval(r.data);
        }
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [tab]);

  return (
    <div>
      <h2 style={{ marginBottom: 8, color: "#f1f5f9" }}>Admin Reports</h2>
      <p style={{ color: "#94a3b8", marginBottom: 24, fontSize: "0.875rem" }}>
        Platform-wide usage statistics, posture accuracy performance, and model evaluation logs.
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        <button style={S.tab(tab === "usage")} onClick={() => setTab("usage")}>
          Usage Statistics
        </button>
        <button style={S.tab(tab === "accuracy")} onClick={() => setTab("accuracy")}>
          Accuracy Performance
        </button>
        <button style={S.tab(tab === "model")} onClick={() => setTab("model")}>
          Model Evaluation
        </button>
      </div>

      {loading && (
        <div style={{ ...S.card, textAlign: "center", color: "#94a3b8" }}>Loading…</div>
      )}

      {/* Usage Statistics */}
      {tab === "usage" && usage && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))",
            gap: 12, marginBottom: 20 }}>
            {[
              { label: "Total Users", value: usage.total_users, color: "#60a5fa" },
              { label: "Active (7d)", value: usage.active_users_7d, color: "#22c55e" },
              { label: "Suspended", value: usage.suspended_users, color: "#ef4444" },
              { label: "Total Sessions", value: usage.total_sessions, color: "#a78bfa" },
              { label: "Sessions (7d)", value: usage.sessions_7d, color: "#f59e0b" },
              { label: "Recommendations", value: usage.total_recommendations_generated, color: "#fb923c" },
            ].map(({ label, value, color }) => (
              <div key={label} style={S.card}>
                <div style={{ fontSize: "2rem", fontWeight: 700, color }}>{value}</div>
                <div style={{ fontSize: "0.78rem", color: "#94a3b8", marginTop: 4 }}>{label}</div>
              </div>
            ))}
          </div>

          <div style={S.card}>
            <h4 style={{ color: "#94a3b8", marginBottom: 12 }}>Platform Health</h4>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div style={S.stat}>
                <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "#f1f5f9" }}>
                  {usage.avg_session_score.toFixed(1)}%
                </div>
                <div style={{ fontSize: "0.78rem", color: "#94a3b8", marginTop: 4 }}>
                  Avg Session Score
                </div>
              </div>
              <div style={S.stat}>
                <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "#f1f5f9" }}>
                  {usage.total_sessions > 0
                    ? (usage.total_sessions / Math.max(usage.total_users, 1)).toFixed(1)
                    : "0"}
                </div>
                <div style={{ fontSize: "0.78rem", color: "#94a3b8", marginTop: 4 }}>
                  Avg Sessions / User
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Accuracy Performance */}
      {tab === "accuracy" && accuracy && (
        <>
          <div style={S.card}>
            <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
              <div>
                <div style={{ fontSize: "2.5rem", fontWeight: 700, color: "#22c55e" }}>
                  {accuracy.overall_avg_accuracy.toFixed(1)}%
                </div>
                <div style={{ color: "#94a3b8", fontSize: "0.875rem" }}>
                  Overall Average Posture Accuracy
                </div>
              </div>
            </div>
          </div>

          <div style={S.card}>
            <h4 style={{ color: "#94a3b8", marginBottom: 16 }}>
              Per-Movement Accuracy (sorted worst → best)
            </h4>
            {accuracy.movement_accuracy.length === 0 ? (
              <p style={{ color: "#64748b" }}>No data yet.</p>
            ) : accuracy.movement_accuracy.map((m, i) => (
              <div key={i} style={{ marginBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between",
                  marginBottom: 4, fontSize: "0.875rem" }}>
                  <span style={{ color: "#f1f5f9" }}>{m.movement}</span>
                  <span style={{ color: "#64748b" }}>{m.count} samples</span>
                </div>
                <ScoreBar value={m.avg_accuracy} />
              </div>
            ))}
          </div>

          <div style={S.card}>
            <h4 style={{ color: "#94a3b8", marginBottom: 16 }}>14-Day Accuracy Trend</h4>
            <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 120 }}>
              {accuracy.accuracy_trend.map((d, i) => {
                const h = Math.max((d.avg_accuracy / 100) * 100, 2);
                const color = d.avg_accuracy >= 70 ? "#22c55e"
                  : d.avg_accuracy >= 50 ? "#f59e0b" : "#ef4444";
                return (
                  <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column",
                    alignItems: "center", gap: 4 }}>
                    <span style={{ fontSize: "0.6rem", color: "#64748b" }}>
                      {d.avg_accuracy > 0 ? d.avg_accuracy.toFixed(0) : ""}
                    </span>
                    <div title={`${d.date}: ${d.avg_accuracy}%`}
                      style={{ width: "100%", height: h, background: color,
                        borderRadius: "2px 2px 0 0", minHeight: 4 }} />
                    <span style={{ fontSize: "0.55rem", color: "#475569",
                      transform: "rotate(-45deg)", whiteSpace: "nowrap" }}>
                      {d.date.slice(5)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* Model Evaluation */}
      {tab === "model" && modelEval && (
        <>
          <div style={S.card}>
            <h4 style={{ color: "#94a3b8", marginBottom: 16 }}>Per-Action Model Metrics</h4>
            {modelEval.per_action_metrics.length === 0 ? (
              <p style={{ color: "#64748b" }}>No session action data recorded yet.</p>
            ) : (
              <div style={{ overflow: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ background: "#0f172a" }}>
                      {["Action", "Total Executions", "Avg Score"].map(h => (
                        <th key={h} style={S.th}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {modelEval.per_action_metrics.map((m, i) => (
                      <tr key={i}>
                        <td style={S.td}><strong>{m.action}</strong></td>
                        <td style={S.td}>{m.total_executions}</td>
                        <td style={{ ...S.td, width: 200 }}>
                          <ScoreBar value={m.avg_score} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div style={S.card}>
            <h4 style={{ color: "#94a3b8", marginBottom: 16 }}>
              Daily Session Metrics (last 30 days)
            </h4>
            {modelEval.daily_metrics.length === 0 ? (
              <p style={{ color: "#64748b" }}>No data yet.</p>
            ) : (
              <div style={{ overflow: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ background: "#0f172a" }}>
                      {["Date", "Sessions", "Avg Score", "Avg FPS", "Avg Latency (ms)"].map(h => (
                        <th key={h} style={S.th}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {modelEval.daily_metrics.map((d, i) => (
                      <tr key={i}>
                        <td style={{ ...S.td, fontFamily: "monospace" }}>{d.date}</td>
                        <td style={S.td}>{d.sessions}</td>
                        <td style={S.td}>
                          <span style={{
                            color: d.avg_score >= 70 ? "#22c55e"
                              : d.avg_score >= 50 ? "#f59e0b" : "#ef4444",
                            fontWeight: 600,
                          }}>{d.avg_score.toFixed(1)}%</span>
                        </td>
                        <td style={S.td}>{d.avg_fps > 0 ? d.avg_fps.toFixed(1) : "—"}</td>
                        <td style={S.td}>{d.avg_latency_ms > 0 ? d.avg_latency_ms.toFixed(0) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
