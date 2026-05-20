import { useEffect, useState } from "react";
import { adminApi } from "../../services/api.js";

const S = {
  card: { background: "#1e293b", borderRadius: 10, padding: 20, marginBottom: 16,
    border: "1px solid #334155" },
  input: {
    background: "#0f172a", border: "1px solid #334155", borderRadius: 6,
    color: "#f1f5f9", padding: "8px 12px", fontSize: "0.875rem",
    width: "100%", boxSizing: "border-box",
  },
  label: { display: "block", fontSize: "0.78rem", color: "#94a3b8", marginBottom: 4 },
  btn: (color = "#3b82f6") => ({
    padding: "7px 16px", borderRadius: 6, border: "none", cursor: "pointer",
    fontSize: "0.82rem", background: color + "22", color, fontWeight: 600,
  }),
  badge: (color) => ({
    display: "inline-block", padding: "2px 10px", borderRadius: 20,
    fontSize: "0.72rem", fontWeight: 600, background: color + "22", color,
  }),
};

const EMPTY_FORM = {
  key: "", label: "", condition_description: "", advice_text: "", priority: 0, is_active: true,
};

export default function AdminRecommendationRules() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // rule id or "new"
  const [form, setForm] = useState(EMPTY_FORM);
  const [msg, setMsg] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await adminApi.listRules();
      setRules(r.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const openNew = () => {
    setForm(EMPTY_FORM);
    setEditing("new");
    setMsg(null);
  };

  const openEdit = (rule) => {
    setForm({
      key: rule.key, label: rule.label,
      condition_description: rule.condition_description || "",
      advice_text: rule.advice_text,
      priority: rule.priority,
      is_active: rule.is_active,
    });
    setEditing(rule.id);
    setMsg(null);
  };

  const cancel = () => { setEditing(null); setMsg(null); };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm(f => ({ ...f, [name]: type === "checkbox" ? checked : value }));
  };

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      const payload = { ...form, priority: Number(form.priority) };
      if (editing === "new") {
        const r = await adminApi.createRule(payload);
        setRules(prev => [r.data, ...prev]);
        setMsg({ type: "success", text: "Rule created" });
      } else {
        const r = await adminApi.updateRule(editing, payload);
        setRules(prev => prev.map(x => x.id === editing ? r.data : x));
        setMsg({ type: "success", text: "Rule updated" });
      }
      setEditing(null);
    } catch (err) {
      setMsg({ type: "error", text: err.response?.data?.detail || "Save failed" });
    } finally {
      setSaving(false);
    }
  };

  const remove = async (rule) => {
    if (!confirm(`Delete rule "${rule.label}"?`)) return;
    try {
      await adminApi.deleteRule(rule.id);
      setRules(prev => prev.filter(x => x.id !== rule.id));
      setMsg({ type: "success", text: "Rule deleted" });
    } catch {
      setMsg({ type: "error", text: "Delete failed" });
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start",
        marginBottom: 24 }}>
        <div>
          <h2 style={{ marginBottom: 4, color: "#f1f5f9" }}>Recommendation Rules</h2>
          <p style={{ color: "#94a3b8", fontSize: "0.875rem" }}>
            Manage the Yangsheng advice rules used for personalised wellness recommendations.
          </p>
        </div>
        <button onClick={openNew} style={{ ...S.btn("#22c55e"), padding: "9px 20px" }}>
          + New Rule
        </button>
      </div>

      {msg && (
        <div style={{ ...S.card, background: msg.type === "success" ? "#16a34a22" : "#dc262622",
          color: msg.type === "success" ? "#4ade80" : "#f87171" }}>
          {msg.text}
        </div>
      )}

      {/* Edit/Create form */}
      {editing !== null && (
        <div style={S.card}>
          <h3 style={{ marginBottom: 16, color: "#f1f5f9" }}>
            {editing === "new" ? "New Rule" : "Edit Rule"}
          </h3>
          <form onSubmit={save}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 14 }}>
              <div>
                <label style={S.label}>Key (unique identifier)</label>
                <input style={S.input} name="key" value={form.key} onChange={handleChange}
                  required disabled={editing !== "new"}
                  placeholder="e.g. high_stress" />
              </div>
              <div>
                <label style={S.label}>Label</label>
                <input style={S.input} name="label" value={form.label} onChange={handleChange}
                  required placeholder="e.g. High Stress Level" />
              </div>
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={S.label}>Condition Description</label>
              <input style={S.input} name="condition_description"
                value={form.condition_description} onChange={handleChange}
                placeholder="e.g. Triggered when stress_level >= 4" />
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={S.label}>Advice Text</label>
              <textarea style={{ ...S.input, minHeight: 100, resize: "vertical" }}
                name="advice_text" value={form.advice_text} onChange={handleChange}
                required placeholder="Personalised advice shown to the user…" />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", gap: 14, marginBottom: 18 }}>
              <div>
                <label style={S.label}>Priority (higher = checked first)</label>
                <input style={S.input} name="priority" type="number" value={form.priority}
                  onChange={handleChange} min={0} max={100} />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 20 }}>
                <input type="checkbox" id="is_active" name="is_active"
                  checked={form.is_active} onChange={handleChange} />
                <label htmlFor="is_active" style={{ color: "#94a3b8", fontSize: "0.875rem",
                  cursor: "pointer" }}>
                  Active (included in recommendation engine)
                </label>
              </div>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button type="submit" disabled={saving}
                style={{ ...S.btn("#3b82f6"), padding: "9px 24px" }}>
                {saving ? "Saving…" : "Save Rule"}
              </button>
              <button type="button" onClick={cancel}
                style={{ ...S.btn("#94a3b8"), padding: "9px 24px" }}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Rules list */}
      {loading ? (
        <div style={{ ...S.card, textAlign: "center", color: "#94a3b8" }}>Loading…</div>
      ) : rules.length === 0 ? (
        <div style={{ ...S.card, textAlign: "center", color: "#64748b" }}>
          No rules yet. Click "+ New Rule" to add the first Yangsheng advice rule.
        </div>
      ) : rules.map(rule => (
        <div key={rule.id} style={S.card}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
                <code style={{ background: "#0f172a", color: "#a78bfa", padding: "2px 8px",
                  borderRadius: 4, fontSize: "0.78rem" }}>{rule.key}</code>
                <span style={S.badge(rule.is_active ? "#22c55e" : "#64748b")}>
                  {rule.is_active ? "Active" : "Inactive"}
                </span>
                <span style={{ fontSize: "0.72rem", color: "#64748b" }}>
                  priority: {rule.priority}
                </span>
              </div>
              <h4 style={{ color: "#f1f5f9", marginBottom: 4 }}>{rule.label}</h4>
              {rule.condition_description && (
                <p style={{ color: "#64748b", fontSize: "0.78rem", marginBottom: 6 }}>
                  Condition: {rule.condition_description}
                </p>
              )}
              <p style={{ color: "#cbd5e1", fontSize: "0.875rem", lineHeight: 1.5 }}>
                {rule.advice_text}
              </p>
              <p style={{ color: "#475569", fontSize: "0.72rem", marginTop: 8 }}>
                Updated: {new Date(rule.updated_at).toLocaleString()}
              </p>
            </div>
            <div style={{ display: "flex", gap: 6, marginLeft: 16 }}>
              <button onClick={() => openEdit(rule)} style={S.btn("#60a5fa")}>Edit</button>
              <button onClick={() => remove(rule)} style={S.btn("#ef4444")}>Delete</button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
