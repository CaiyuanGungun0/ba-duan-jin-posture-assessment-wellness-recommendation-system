import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, Title, Tooltip, Legend, Filler,
} from "chart.js";
import { Line, Bar } from "react-chartjs-2";
import CircularProgress from "../components/CircularProgress";
import RecommendationCard from "../components/RecommendationCard";
import SessionTimeline from "../components/SessionTimeline";
import { dashboardApi, sessionsApi } from "../services/api";
import { useAuth } from "../services/auth.jsx";

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, Title, Tooltip, Legend, Filler
);

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([dashboardApi.summary(), sessionsApi.list(10)])
      .then(([s, sess]) => {
        setSummary(s.data);
        setSessions(sess.data);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="spinner" />;

  const weekly = summary?.weekly_stats ?? {};
  const history = summary?.progress_history ?? [];
  const movements = summary?.movement_breakdown ?? [];

  const lineData = {
    labels: history.map((h) => h.date.slice(5)),
    datasets: [{
      label: "Avg Accuracy (%)",
      data: history.map((h) => h.avg_score),
      fill: true,
      borderColor: "#4a7c59",
      backgroundColor: "rgba(74,124,89,0.12)",
      tension: 0.4,
      pointRadius: 4,
      pointBackgroundColor: "#4a7c59",
    }],
  };

  const barData = {
    labels: movements.map((m) => m.movement_name),
    datasets: [{
      label: "Avg Accuracy (%)",
      data: movements.map((m) => m.avg_accuracy),
      backgroundColor: movements.map((m) =>
        m.avg_accuracy >= 80 ? "rgba(74,124,89,0.7)" :
        m.avg_accuracy >= 60 ? "rgba(143,201,156,0.7)" : "rgba(224,82,82,0.6)"
      ),
      borderRadius: 8,
    }],
  };

  const chartOpts = {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: {
      y: { min: 0, max: 100, grid: { color: "#f0ece4" } },
      x: { grid: { display: false } },
    },
  };

  return (
    <div className="page-container">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ marginBottom: 4 }}>
            Welcome back{user ? `, ${user.username}` : ""}
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
            Your Ba Duan Jin wellness overview
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate("/session")}>
          Start Session
        </button>
      </div>

      {/* Stat tiles */}
      <div className="grid-3" style={{ marginBottom: 20 }}>
        <div className="stat-tile">
          <span className="label">Sessions this week</span>
          <span className="value">{weekly.sessions_this_week ?? 0}</span>
          <span className="sub">{weekly.streak_days ?? 0}-day streak</span>
        </div>
        <div className="stat-tile">
          <span className="label">Practice time</span>
          <span className="value">{weekly.total_minutes ?? 0}<span style={{ fontSize: "1rem", fontWeight: 400 }}>min</span></span>
          <span className="sub">this week</span>
        </div>
        <div className="stat-tile">
          <span className="label">Best accuracy</span>
          <span className="value">{weekly.best_accuracy ?? 0}<span style={{ fontSize: "1rem", fontWeight: 400 }}>%</span></span>
          <span className="sub">avg {weekly.avg_accuracy ?? 0}%</span>
        </div>
      </div>

      {/* Main row */}
      <div className="grid-2" style={{ marginBottom: 20 }}>
        {/* Progress chart */}
        <div className="card">
          <p className="section-title">14-Day Progress</p>
          {history.length > 0 ? (
            <Line data={lineData} options={chartOpts} />
          ) : (
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
              No data yet — complete your first session to start tracking.
            </p>
          )}
        </div>

        {/* Circular accuracy + recommendation */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="card" style={{ display: "flex", alignItems: "center", gap: 20 }}>
            <CircularProgress value={weekly.avg_accuracy ?? 0} size={90} label="Avg Accuracy" />
            <div>
              <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Overall posture quality</p>
              <p style={{ fontSize: "1.35rem", fontWeight: 600, color: "var(--green-700)" }}>
                {(weekly.avg_accuracy ?? 0) >= 80 ? "Excellent" :
                 (weekly.avg_accuracy ?? 0) >= 65 ? "Good" :
                 (weekly.avg_accuracy ?? 0) > 0 ? "Improving" : "—"}
              </p>
            </div>
          </div>
          <RecommendationCard recommendation={summary?.latest_recommendation} />
        </div>
      </div>

      {/* Movement breakdown */}
      {movements.length > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <p className="section-title">Movement Accuracy (30 days)</p>
          <Bar data={barData} options={chartOpts} />
        </div>
      )}

      {/* Recent sessions */}
      <div className="card">
        <p className="section-title">Recent Sessions</p>
        <SessionTimeline sessions={sessions} />
      </div>
    </div>
  );
}
