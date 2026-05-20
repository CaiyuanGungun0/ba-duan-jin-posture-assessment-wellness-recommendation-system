import { useEffect, useState } from "react";
import { reportsApi } from "../services/api.js";

const TREND_STYLES = {
  improving: { color: "var(--green-500)", icon: "📈" },
  stable: { color: "#e09c27", icon: "📊" },
  declining: { color: "#e05252", icon: "📉" },
};

export default function Reports() {
  const [reports, setReports] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    const r = await reportsApi.list();
    setReports(r.data);
    setLoading(false);
  };

  useEffect(() => { refresh(); }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await reportsApi.generate();
      refresh();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to generate report");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return <div className="spinner" />;

  return (
    <div className="page-container">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <h1>Health Reports</h1>
        <button className="btn btn-primary" onClick={handleGenerate} disabled={generating}>
          {generating ? "Generating…" : "Generate Weekly Report"}
        </button>
      </div>
      <p style={{ color: "var(--text-muted)", marginBottom: 24 }}>
        AI-powered weekly analysis of your posture, wellness, and progress
      </p>

      {reports.length === 0 ? (
        <div className="empty-state">
          <p>No reports yet. Generate your first weekly health report!</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {reports.map(report => {
            const trend = TREND_STYLES[report.posture_trend] || TREND_STYLES.stable;
            const riskColor = report.risk_score <= 3 ? "var(--green-500)" : report.risk_score <= 6 ? "#e09c27" : "#e05252";
            return (
              <div key={report.id} className="card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
                  <div>
                    <h3>Weekly Health Report</h3>
                    <p style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
                      {new Date(report.generated_at).toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
                    </p>
                  </div>
                  <div style={{ display: "flex", gap: 12 }}>
                    {report.posture_trend && (
                      <div style={{ textAlign: "center" }}>
                        <div style={{ fontSize: "1.4rem" }}>{trend.icon}</div>
                        <div style={{ fontSize: "0.7rem", color: trend.color, fontWeight: 600 }}>
                          {report.posture_trend?.charAt(0).toUpperCase() + report.posture_trend?.slice(1)}
                        </div>
                      </div>
                    )}
                    {report.risk_score !== null && (
                      <div style={{ textAlign: "center" }}>
                        <div style={{ fontSize: "1.4rem", fontWeight: 700, color: riskColor }}>{report.risk_score}</div>
                        <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Risk /10</div>
                      </div>
                    )}
                  </div>
                </div>

                <div style={{
                  background: "var(--beige-100)", borderRadius: 10, padding: "12px 16px",
                  fontFamily: "monospace", fontSize: "0.82rem", lineHeight: 1.7,
                  whiteSpace: "pre-wrap", marginBottom: 16,
                }}>
                  {report.summary}
                </div>

                {report.recommendation && (
                  <div>
                    <p style={{ fontWeight: 600, marginBottom: 8, fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                      Recommendations
                    </p>
                    <div style={{ fontSize: "0.85rem", lineHeight: 1.8, color: "var(--text-primary)" }}>
                      {report.recommendation}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
