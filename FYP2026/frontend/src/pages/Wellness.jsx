import { useEffect, useState } from "react";
import { wellnessApi } from "../services/api.js";

const MOODS = [
  { value: "great", emoji: "😄", label: "Great" },
  { value: "good", emoji: "🙂", label: "Good" },
  { value: "neutral", emoji: "😐", label: "Neutral" },
  { value: "low", emoji: "😔", label: "Low" },
  { value: "anxious", emoji: "😰", label: "Anxious" },
];

const WATER_PRESETS = [150, 250, 350, 500];

export default function Wellness() {
  const [summary, setSummary] = useState(null);
  const [todayLog, setTodayLog] = useState(null);
  const [waterToday, setWaterToday] = useState(null);
  const [loading, setLoading] = useState(true);

  const [healthForm, setHealthForm] = useState({
    log_date: new Date().toISOString().split("T")[0],
    sleep_hours: "",
    stress_level: "",
    mood: "",
    steps: "",
    weight_kg: "",
    notes: "",
  });
  const [foodForm, setFoodForm] = useState({ meal_type: "breakfast", food_name: "", quantity: "", calories: "" });
  const [foodLogs, setFoodLogs] = useState([]);
  const [savingHealth, setSavingHealth] = useState(false);
  const [savingFood, setSavingFood] = useState(false);
  const [msg, setMsg] = useState(null);

  const refresh = async () => {
    const [sum, today, water, foods] = await Promise.all([
      wellnessApi.summary(7),
      wellnessApi.todayHealthLog(),
      wellnessApi.todayWater(),
      wellnessApi.listFood(1),
    ]);
    setSummary(sum.data);
    setTodayLog(today.data);
    setWaterToday(water.data);
    setFoodLogs(foods.data);
    if (today.data) {
      setHealthForm(f => ({
        ...f,
        sleep_hours: today.data.sleep_hours ?? "",
        stress_level: today.data.stress_level ?? "",
        mood: today.data.mood ?? "",
        steps: today.data.steps ?? "",
        weight_kg: today.data.weight_kg ?? "",
        notes: today.data.notes ?? "",
      }));
    }
    setLoading(false);
  };

  useEffect(() => { refresh(); }, []);

  const handleHealthSubmit = async (e) => {
    e.preventDefault();
    setSavingHealth(true);
    setMsg(null);
    try {
      await wellnessApi.upsertHealthLog({
        ...healthForm,
        log_date: new Date(healthForm.log_date).toISOString(),
        sleep_hours: healthForm.sleep_hours ? Number(healthForm.sleep_hours) : null,
        stress_level: healthForm.stress_level ? Number(healthForm.stress_level) : null,
        steps: Number(healthForm.steps) || 0,
        weight_kg: healthForm.weight_kg ? Number(healthForm.weight_kg) : null,
      });
      setMsg({ type: "success", text: "Health log saved!" });
      refresh();
    } catch {
      setMsg({ type: "error", text: "Failed to save health log" });
    } finally {
      setSavingHealth(false);
    }
  };

  const handleWaterAdd = async (ml) => {
    try {
      await wellnessApi.addWater(ml);
      refresh();
    } catch {}
  };

  const handleFoodSubmit = async (e) => {
    e.preventDefault();
    setSavingFood(true);
    try {
      await wellnessApi.addFood({ ...foodForm, calories: Number(foodForm.calories) || 0 });
      setFoodForm({ meal_type: "breakfast", food_name: "", quantity: "", calories: "" });
      refresh();
    } catch {}
    setSavingFood(false);
  };

  const handleDeleteFood = async (id) => {
    await wellnessApi.deleteFood(id);
    refresh();
  };

  if (loading) return <div className="spinner" />;

  const waterPct = waterToday ? Math.min(100, Math.round(waterToday.total_ml / Math.max(1, waterToday.target_ml) * 100)) : 0;

  return (
    <div className="page-container">
      <h1 style={{ marginBottom: 8 }}>Wellness Tracker</h1>
      <p style={{ color: "var(--text-muted)", marginBottom: 24 }}>Track your daily health, nutrition, and mental wellbeing</p>

      {/* Weekly summary */}
      {summary && summary.days_logged > 0 && (
        <div className="grid-3" style={{ marginBottom: 24 }}>
          {[
            { label: "Avg Sleep", value: `${summary.avg_sleep_hours}h` },
            { label: "Avg Stress", value: `${summary.avg_stress_level}/10` },
            { label: "Days Logged", value: summary.days_logged },
            { label: "Total Water", value: `${(summary.total_water_ml / 1000).toFixed(1)}L` },
            { label: "Avg Steps", value: summary.avg_steps.toLocaleString() },
            {
              label: "Top Mood",
              value: Object.entries(summary.mood_distribution || {}).sort((a, b) => b[1] - a[1])[0]?.[0] || "—",
            },
          ].map(s => (
            <div className="stat-tile" key={s.label}>
              <span className="label">{s.label}</span>
              <span className="value" style={{ fontSize: "1.5rem" }}>{s.value}</span>
            </div>
          ))}
        </div>
      )}

      <div className="grid-2" style={{ gap: 24, alignItems: "start" }}>
        {/* Left column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Daily health log */}
          <div className="card">
            <h3 style={{ marginBottom: 16 }}>Today's Health Log</h3>
            <form onSubmit={handleHealthSubmit}>
              {/* Mood selector */}
              <div className="form-group">
                <label>Mood</label>
                <div style={{ display: "flex", gap: 8 }}>
                  {MOODS.map(m => (
                    <button
                      key={m.value} type="button"
                      onClick={() => setHealthForm(f => ({ ...f, mood: m.value }))}
                      style={{
                        flex: 1, padding: "8px 4px", borderRadius: 10, border: "2px solid",
                        borderColor: healthForm.mood === m.value ? "var(--green-500)" : "var(--beige-300)",
                        background: healthForm.mood === m.value ? "var(--green-50)" : "#fff",
                        cursor: "pointer", fontSize: "1.2rem", display: "flex", flexDirection: "column",
                        alignItems: "center", gap: 2,
                      }}
                    >
                      <span>{m.emoji}</span>
                      <span style={{ fontSize: "0.65rem", color: "var(--text-muted)" }}>{m.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid-2">
                <div className="form-group">
                  <label>Sleep (hours)</label>
                  <input type="number" step={0.5} min={0} max={24} value={healthForm.sleep_hours}
                    onChange={e => setHealthForm(f => ({ ...f, sleep_hours: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label>Stress (1-10)</label>
                  <input type="number" min={1} max={10} value={healthForm.stress_level}
                    onChange={e => setHealthForm(f => ({ ...f, stress_level: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label>Steps</label>
                  <input type="number" min={0} value={healthForm.steps}
                    onChange={e => setHealthForm(f => ({ ...f, steps: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label>Weight (kg)</label>
                  <input type="number" step={0.1} min={10} max={500} value={healthForm.weight_kg}
                    onChange={e => setHealthForm(f => ({ ...f, weight_kg: e.target.value }))} />
                </div>
              </div>
              <div className="form-group">
                <label>Notes</label>
                <input type="text" value={healthForm.notes}
                  onChange={e => setHealthForm(f => ({ ...f, notes: e.target.value }))}
                  placeholder="How do you feel today?" />
              </div>
              {msg && (
                <p style={{ color: msg.type === "success" ? "var(--green-500)" : "#e05252", fontSize: "0.85rem", marginBottom: 8 }}>
                  {msg.text}
                </p>
              )}
              <button className="btn btn-primary" type="submit" disabled={savingHealth} style={{ width: "100%" }}>
                {savingHealth ? "Saving…" : "Save Log"}
              </button>
            </form>
          </div>

          {/* Water tracker */}
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Water Intake 💧</h3>
            {waterToday && (
              <>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: "0.85rem" }}>
                  <span>{waterToday.total_ml} ml consumed</span>
                  <span style={{ color: "var(--text-muted)" }}>Target: {waterToday.target_ml} ml</span>
                </div>
                <div style={{ height: 10, background: "var(--beige-200)", borderRadius: 5, marginBottom: 16 }}>
                  <div style={{
                    height: "100%", borderRadius: 5,
                    background: waterPct >= 100 ? "var(--green-400)" : "var(--green-500)",
                    width: `${waterPct}%`, transition: "width 0.4s",
                  }} />
                </div>
              </>
            )}
            <div style={{ display: "flex", gap: 8 }}>
              {WATER_PRESETS.map(ml => (
                <button key={ml} className="btn btn-outline" onClick={() => handleWaterAdd(ml)}
                  style={{ flex: 1, fontSize: "0.8rem", padding: "8px 4px" }}>
                  +{ml}ml
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right column - Food log */}
        <div className="card">
          <h3 style={{ marginBottom: 16 }}>Food Log 🥗</h3>
          <form onSubmit={handleFoodSubmit}>
            <div className="form-group">
              <label>Meal Type</label>
              <select value={foodForm.meal_type} onChange={e => setFoodForm(f => ({ ...f, meal_type: e.target.value }))} className="form-select">
                {["breakfast", "lunch", "dinner", "snack"].map(m => (
                  <option key={m} value={m}>{m.charAt(0).toUpperCase() + m.slice(1)}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Food Name</label>
              <input value={foodForm.food_name} onChange={e => setFoodForm(f => ({ ...f, food_name: e.target.value }))}
                placeholder="e.g. Brown rice" required />
            </div>
            <div className="grid-2">
              <div className="form-group">
                <label>Quantity</label>
                <input value={foodForm.quantity} onChange={e => setFoodForm(f => ({ ...f, quantity: e.target.value }))}
                  placeholder="e.g. 1 cup" />
              </div>
              <div className="form-group">
                <label>Calories</label>
                <input type="number" value={foodForm.calories} onChange={e => setFoodForm(f => ({ ...f, calories: e.target.value }))}
                  min={0} placeholder="kcal" />
              </div>
            </div>
            <button className="btn btn-primary" type="submit" disabled={savingFood} style={{ width: "100%", marginBottom: 16 }}>
              {savingFood ? "Adding…" : "Add Food"}
            </button>
          </form>

          {/* Today's food list */}
          {foodLogs.length > 0 && (
            <>
              <p className="section-title">Today's Food</p>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {foodLogs.map(f => (
                  <div key={f.id} style={{
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                    padding: "8px 12px", background: "var(--beige-100)", borderRadius: 8,
                  }}>
                    <div>
                      <span style={{ fontWeight: 500, fontSize: "0.9rem" }}>{f.food_name}</span>
                      <span style={{ color: "var(--text-muted)", fontSize: "0.78rem", marginLeft: 8 }}>
                        {f.meal_type} {f.quantity ? `· ${f.quantity}` : ""}
                      </span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: "0.85rem", color: "var(--green-700)" }}>{f.calories} kcal</span>
                      <button onClick={() => handleDeleteFood(f.id)}
                        style={{ background: "none", border: "none", cursor: "pointer", color: "#e05252", fontSize: 14 }}>
                        ✕
                      </button>
                    </div>
                  </div>
                ))}
                <div style={{ textAlign: "right", fontSize: "0.85rem", color: "var(--text-muted)", paddingTop: 4 }}>
                  Total: <strong>{foodLogs.reduce((s, f) => s + f.calories, 0).toFixed(0)} kcal</strong>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
