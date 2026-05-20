import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { exerciseApi, socialApi } from "../services/api.js";

const DIFFICULTY_COLORS = { beginner: "#4a7c59", intermediate: "#e09c27", advanced: "#e05252" };
const CATEGORY_ICONS = { baduanjin: "🧘", breathing: "🌬️", meditation: "🕯️" };

export default function ExerciseLibrary() {
  const [exercises, setExercises] = useState([]);
  const [favorites, setFavorites] = useState(new Set());
  const [filter, setFilter] = useState({ category: "", difficulty: "" });
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const navigate = useNavigate();

  const refresh = async () => {
    const [exR, favR] = await Promise.all([
      exerciseApi.list(filter.category, filter.difficulty),
      socialApi.favorites(),
    ]);
    setExercises(exR.data);
    setFavorites(new Set(favR.data.map(f => f.exercise.id)));
    setLoading(false);
  };

  useEffect(() => { refresh(); }, [filter]);

  const handleFavorite = async (id) => {
    try {
      if (favorites.has(id)) {
        await socialApi.removeFavorite(id);
        setFavorites(prev => { const s = new Set(prev); s.delete(id); return s; });
      } else {
        await socialApi.addFavorite(id);
        setFavorites(prev => new Set([...prev, id]));
      }
    } catch {}
  };

  const handleStartSession = (exercise) => {
    navigate("/session", { state: { exercise } });
  };

  if (loading) return <div className="spinner" />;

  return (
    <div className="page-container">
      <h1 style={{ marginBottom: 8 }}>Exercise Library</h1>
      <p style={{ color: "var(--text-muted)", marginBottom: 24 }}>
        Explore all 8 Ba Duan Jin movements and wellness exercises
      </p>

      {/* Filters */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        <select className="form-select" style={{ width: "auto", padding: "8px 14px" }}
          value={filter.category} onChange={e => setFilter(f => ({ ...f, category: e.target.value }))}>
          <option value="">All Categories</option>
          <option value="baduanjin">🧘 Ba Duan Jin</option>
          <option value="breathing">🌬️ Breathing</option>
          <option value="meditation">🕯️ Meditation</option>
        </select>
        <select className="form-select" style={{ width: "auto", padding: "8px 14px" }}
          value={filter.difficulty} onChange={e => setFilter(f => ({ ...f, difficulty: e.target.value }))}>
          <option value="">All Levels</option>
          <option value="beginner">Beginner</option>
          <option value="intermediate">Intermediate</option>
          <option value="advanced">Advanced</option>
        </select>
        <span style={{ color: "var(--text-muted)", fontSize: "0.85rem", alignSelf: "center" }}>
          {exercises.length} exercises
        </span>
      </div>

      {/* Exercise grid */}
      <div className="exercise-library-grid">
        {exercises.map(ex => (
          <div
            key={ex.id}
            className={`exercise-card ${selected?.id === ex.id ? "selected" : ""}`}
            onClick={() => setSelected(selected?.id === ex.id ? null : ex)}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
              <span style={{ fontSize: "1.8rem" }}>{CATEGORY_ICONS[ex.category] || "🏃"}</span>
              <button
                onClick={e => { e.stopPropagation(); handleFavorite(ex.id); }}
                style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1.2rem" }}
              >
                {favorites.has(ex.id) ? "❤️" : "🤍"}
              </button>
            </div>
            {ex.action_no && (
              <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: 4 }}>
                Movement {ex.action_no}
              </div>
            )}
            <div style={{ fontWeight: 600, fontSize: "0.95rem", marginBottom: 4 }}>{ex.name}</div>
            {ex.name_zh && <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: 8 }}>{ex.name_zh}</div>}
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
              <span style={{
                fontSize: "0.7rem", padding: "2px 8px", borderRadius: 20,
                background: DIFFICULTY_COLORS[ex.difficulty] + "20",
                color: DIFFICULTY_COLORS[ex.difficulty], fontWeight: 600,
              }}>
                {ex.difficulty}
              </span>
              <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                ⏱ {Math.round(ex.duration_seconds / 60)} min
              </span>
              <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                🔥 ~{ex.calories_est} kcal
              </span>
            </div>

            {selected?.id === ex.id && (
              <div style={{ borderTop: "1px solid var(--beige-200)", paddingTop: 12, marginTop: 4 }}>
                {ex.description && (
                  <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: 8 }}>
                    {ex.description}
                  </p>
                )}
                {ex.benefits && (
                  <div style={{ marginBottom: 8 }}>
                    <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: 4 }}>BENEFITS</p>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                      {JSON.parse(ex.benefits || "[]").map(b => (
                        <span key={b} style={{
                          fontSize: "0.72rem", padding: "2px 8px", borderRadius: 20,
                          background: "var(--green-50)", color: "var(--green-700)",
                        }}>{b}</span>
                      ))}
                    </div>
                  </div>
                )}
                <button
                  className="btn btn-primary"
                  onClick={e => { e.stopPropagation(); handleStartSession(ex); }}
                  style={{ width: "100%", marginTop: 8 }}
                >
                  Start Practice →
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {exercises.length === 0 && (
        <div className="empty-state">
          <p>No exercises match your filters.</p>
        </div>
      )}
    </div>
  );
}
