import { useEffect, useRef, useState } from "react";
import { useAuth } from "../services/auth.jsx";
import api, { profileApi } from "../services/api.js";

const GOALS = [
  { value: "lose_weight", label: "Lose Weight" },
  { value: "maintain_health", label: "Maintain Health" },
  { value: "improve_flexibility", label: "Improve Flexibility" },
  { value: "improve_posture", label: "Improve Posture" },
  { value: "stress_relief", label: "Stress Relief" },
];

const ACTIVITY_LEVELS = [
  { value: "sedentary", label: "Sedentary (desk job, little exercise)" },
  { value: "light", label: "Light (1-3 days/week exercise)" },
  { value: "moderate", label: "Moderate (3-5 days/week exercise)" },
  { value: "active", label: "Active (6-7 days/week exercise)" },
  { value: "very_active", label: "Very Active (athlete level)" },
];

const HEALTH_CONDITIONS = [
  "neck_pain", "shoulder_pain", "lumbar_discomfort", "hypertension",
  "knee_pain", "diabetes", "heart_condition", "none",
];

export default function Profile() {
  const { user, refreshUser } = useAuth();
  const [stats, setStats] = useState(null);
  const [form, setForm] = useState({});
  const [conditions, setConditions] = useState([]);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);
  const [pwForm, setPwForm] = useState({ current_password: "", new_password: "", confirm: "" });
  const [pwMsg, setPwMsg] = useState(null);
  const [avatarLoading, setAvatarLoading] = useState(false);
  const fileRef = useRef();

  useEffect(() => {
    if (!user) return;
    setForm({
      age: user.age || "",
      gender: user.gender || "",
      height_cm: user.height_cm || "",
      weight_kg: user.weight_kg || "",
      stress_level: user.stress_level || "",
      sleep_quality: user.sleep_quality || "",
      target_goal: user.target_goal || "",
      activity_level: user.activity_level || "",
      target_exercise_minutes: user.target_exercise_minutes || 30,
      target_calories: user.target_calories || 2000,
      target_water_ml: user.target_water_ml || 2000,
      target_sleep_hours: user.target_sleep_hours || 8,
      allow_social_sharing: user.allow_social_sharing ?? true,
      is_public_profile: user.is_public_profile ?? true,
    });
    try {
      setConditions(JSON.parse(user.health_conditions || "[]"));
    } catch {
      setConditions([]);
    }
    profileApi.stats().then(r => setStats(r.data));
  }, [user]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm(f => ({ ...f, [name]: type === "checkbox" ? checked : value }));
  };

  const toggleCondition = (c) => {
    setConditions(prev =>
      prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c]
    );
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      await profileApi.update({
        ...form,
        age: form.age ? Number(form.age) : null,
        height_cm: form.height_cm ? Number(form.height_cm) : null,
        weight_kg: form.weight_kg ? Number(form.weight_kg) : null,
        stress_level: form.stress_level ? Number(form.stress_level) : null,
        sleep_quality: form.sleep_quality ? Number(form.sleep_quality) : null,
        target_exercise_minutes: Number(form.target_exercise_minutes),
        target_calories: Number(form.target_calories),
        target_water_ml: Number(form.target_water_ml),
        target_sleep_hours: Number(form.target_sleep_hours),
        health_conditions: JSON.stringify(conditions),
      });
      await refreshUser();
      setMsg({ type: "success", text: "Profile updated successfully!" });
    } catch (err) {
      setMsg({ type: "error", text: err.response?.data?.detail || "Update failed" });
    } finally {
      setSaving(false);
    }
  };

  const handlePwChange = async (e) => {
    e.preventDefault();
    setPwMsg(null);
    if (pwForm.new_password !== pwForm.confirm) {
      setPwMsg({ type: "error", text: "Passwords don't match" });
      return;
    }
    try {
      await profileApi.changePassword({
        current_password: pwForm.current_password,
        new_password: pwForm.new_password,
      });
      setPwForm({ current_password: "", new_password: "", confirm: "" });
      setPwMsg({ type: "success", text: "Password changed successfully!" });
    } catch (err) {
      setPwMsg({ type: "error", text: err.response?.data?.detail || "Failed to change password" });
    }
  };

  const handleAvatarUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarLoading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      await api.post("/profile/avatar", fd, { headers: { "Content-Type": "multipart/form-data" } });
      await refreshUser();
    } catch (err) {
      alert(err.response?.data?.detail || "Avatar upload failed");
    } finally {
      setAvatarLoading(false);
    }
  };

  if (!user) return <div className="spinner" />;

  const bmi = form.height_cm && form.weight_kg
    ? (Number(form.weight_kg) / Math.pow(Number(form.height_cm) / 100, 2)).toFixed(1)
    : user.bmi?.toFixed(1);

  const levelColors = { Bronze: "#cd7f32", Silver: "#aaa", Gold: "#ffd700", Platinum: "#e5e4e2" };

  return (
    <div className="page-container">
      <h1 style={{ marginBottom: 24 }}>My Profile</h1>

      {/* Stats bar */}
      {stats && (
        <div className="grid-3" style={{ marginBottom: 24 }}>
          {[
            { label: "Sessions", value: stats.total_sessions },
            { label: "Minutes", value: stats.total_minutes },
            { label: "Points", value: stats.total_points },
            { label: "Level", value: stats.level },
            { label: "Streak", value: `${stats.streak_days}d` },
            { label: "Badges", value: stats.achievements_count },
          ].map(s => (
            <div className="stat-tile" key={s.label}>
              <span className="label">{s.label}</span>
              <span className="value" style={s.label === "Level" ? { color: levelColors[s.value] } : {}}>
                {s.value}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="grid-2" style={{ gap: 24, alignItems: "start" }}>
        {/* Left: Avatar + basic info */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="card" style={{ textAlign: "center" }}>
            <div style={{ position: "relative", display: "inline-block", marginBottom: 16 }}>
              <img
                src={user.profile_photo ? `http://localhost:8000${user.profile_photo}` : `https://ui-avatars.com/api/?name=${user.username}&size=120&background=4a7c59&color=fff`}
                alt="avatar"
                style={{ width: 100, height: 100, borderRadius: "50%", objectFit: "cover", border: "3px solid var(--green-300)" }}
              />
              <button
                onClick={() => fileRef.current?.click()}
                disabled={avatarLoading}
                style={{
                  position: "absolute", bottom: 0, right: 0,
                  background: "var(--green-500)", color: "#fff",
                  border: "none", borderRadius: "50%", width: 30, height: 30,
                  cursor: "pointer", fontSize: 14,
                }}
              >
                {avatarLoading ? "..." : "✏️"}
              </button>
              <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handleAvatarUpload} />
            </div>
            <h2>{user.username}</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>{user.email}</p>
            <span style={{
              display: "inline-block", marginTop: 8,
              padding: "4px 14px", borderRadius: 20,
              background: levelColors[user.level] + "22",
              color: levelColors[user.level], fontWeight: 600, fontSize: "0.85rem",
            }}>
              {user.level} · {user.total_points} pts
            </span>
          </div>

          {/* Password change */}
          <div className="card">
            <h3 style={{ marginBottom: 16 }}>Change Password</h3>
            <form onSubmit={handlePwChange}>
              {[
                { name: "current_password", label: "Current Password" },
                { name: "new_password", label: "New Password" },
                { name: "confirm", label: "Confirm New Password" },
              ].map(f => (
                <div className="form-group" key={f.name}>
                  <label>{f.label}</label>
                  <input
                    type="password" name={f.name}
                    value={pwForm[f.name]}
                    onChange={e => setPwForm(p => ({ ...p, [e.target.name]: e.target.value }))}
                    required
                  />
                </div>
              ))}
              {pwMsg && (
                <p style={{ color: pwMsg.type === "success" ? "var(--green-500)" : "#e05252", fontSize: "0.85rem", marginBottom: 8 }}>
                  {pwMsg.text}
                </p>
              )}
              <button className="btn btn-outline" type="submit" style={{ width: "100%" }}>
                Update Password
              </button>
            </form>
          </div>
        </div>

        {/* Right: Profile form */}
        <div className="card">
          <h3 style={{ marginBottom: 20 }}>Profile Details</h3>
          <form onSubmit={handleSave}>
            <div className="grid-2">
              <div className="form-group">
                <label>Age</label>
                <input type="number" name="age" value={form.age} onChange={handleChange} min={1} max={120} />
              </div>
              <div className="form-group">
                <label>Gender</label>
                <select name="gender" value={form.gender} onChange={handleChange} className="form-select">
                  <option value="">Select</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                  <option value="prefer_not">Prefer not to say</option>
                </select>
              </div>
              <div className="form-group">
                <label>Height (cm)</label>
                <input type="number" name="height_cm" value={form.height_cm} onChange={handleChange} min={50} max={300} />
              </div>
              <div className="form-group">
                <label>Weight (kg)</label>
                <input type="number" name="weight_kg" value={form.weight_kg} onChange={handleChange} min={10} max={500} step={0.1} />
              </div>
            </div>
            {bmi && (
              <div style={{ marginBottom: 16, padding: "8px 14px", background: "var(--green-50)", borderRadius: 8, fontSize: "0.85rem" }}>
                BMI: <strong>{bmi}</strong> — {Number(bmi) < 18.5 ? "Underweight" : Number(bmi) < 25 ? "Normal" : Number(bmi) < 30 ? "Overweight" : "Obese"}
              </div>
            )}

            <p className="section-title" style={{ marginTop: 8 }}>Wellbeing</p>
            <div className="grid-2">
              <div className="form-group">
                <label>Stress Level (1 = low, 5 = very high)</label>
                <select name="stress_level" value={form.stress_level} onChange={handleChange} className="form-select">
                  <option value="">Not specified</option>
                  {[1,2,3,4,5].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Sleep Quality (1 = poor, 5 = excellent)</label>
                <select name="sleep_quality" value={form.sleep_quality} onChange={handleChange} className="form-select">
                  <option value="">Not specified</option>
                  {[1,2,3,4,5].map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>Fitness Goal</label>
              <select name="target_goal" value={form.target_goal} onChange={handleChange} className="form-select">
                <option value="">Select your goal</option>
                {GOALS.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label>Activity Level</label>
              <select name="activity_level" value={form.activity_level} onChange={handleChange} className="form-select">
                <option value="">Select activity level</option>
                {ACTIVITY_LEVELS.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
              </select>
            </div>

            <p className="section-title" style={{ marginTop: 8 }}>Daily Targets</p>
            <div className="grid-2">
              {[
                { name: "target_exercise_minutes", label: "Exercise (min)", min: 5, max: 480 },
                { name: "target_calories", label: "Calories (kcal)", min: 500, max: 10000 },
                { name: "target_water_ml", label: "Water (ml)", min: 500, max: 10000 },
                { name: "target_sleep_hours", label: "Sleep (hours)", min: 3, max: 14, step: 0.5 },
              ].map(f => (
                <div className="form-group" key={f.name}>
                  <label>{f.label}</label>
                  <input type="number" name={f.name} value={form[f.name]} onChange={handleChange}
                    min={f.min} max={f.max} step={f.step || 1} />
                </div>
              ))}
            </div>

            <p className="section-title" style={{ marginTop: 8 }}>Health Conditions</p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
              {HEALTH_CONDITIONS.map(c => (
                <button
                  key={c} type="button"
                  onClick={() => toggleCondition(c)}
                  className={conditions.includes(c) ? "btn btn-primary" : "btn btn-outline"}
                  style={{ padding: "5px 12px", fontSize: "0.8rem" }}
                >
                  {c.replace(/_/g, " ")}
                </button>
              ))}
            </div>

            <p className="section-title">Privacy Settings</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
              {[
                { name: "is_public_profile", label: "Public profile (visible in leaderboard)" },
                { name: "allow_social_sharing", label: "Allow social sharing (post sessions)" },
              ].map(f => (
                <label key={f.name} style={{ display: "flex", gap: 10, alignItems: "center", cursor: "pointer", fontSize: "0.9rem" }}>
                  <input type="checkbox" name={f.name} checked={!!form[f.name]} onChange={handleChange} />
                  {f.label}
                </label>
              ))}
            </div>

            {msg && (
              <p style={{ color: msg.type === "success" ? "var(--green-500)" : "#e05252", marginBottom: 12, fontSize: "0.85rem" }}>
                {msg.text}
              </p>
            )}
            <button className="btn btn-primary" type="submit" disabled={saving} style={{ width: "100%" }}>
              {saving ? "Saving…" : "Save Profile"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
