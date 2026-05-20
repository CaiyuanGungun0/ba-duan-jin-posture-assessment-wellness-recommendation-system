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

export default function AdminUserManagement() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("");
  const [msg, setMsg] = useState(null);

  const load = async (q = "", f = "") => {
    setLoading(true);
    try {
      const params = {};
      if (q) params.search = q;
      if (f === "suspended") params.suspended = true;
      else if (f === "admin") params.role = "admin";
      const r = await adminApi.listUsers(params);
      setUsers(r.data);
    } catch {
      setMsg({ type: "error", text: "Failed to load users" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    load(search, filter);
  };

  const suspend = async (user) => {
    const next = !user.is_suspended;
    try {
      await adminApi.updateUser(user.id, { is_suspended: next });
      setUsers(u => u.map(x => x.id === user.id ? { ...x, is_suspended: next } : x));
      setMsg({ type: "success", text: `User ${next ? "suspended" : "unsuspended"}` });
    } catch {
      setMsg({ type: "error", text: "Action failed" });
    }
  };

  const promote = async (user) => {
    const next = user.role === "admin" ? "user" : "admin";
    if (!confirm(`Change role to "${next}" for ${user.username}?`)) return;
    try {
      await adminApi.updateUser(user.id, { role: next });
      setUsers(u => u.map(x => x.id === user.id ? { ...x, role: next } : x));
      setMsg({ type: "success", text: `Role changed to ${next}` });
    } catch {
      setMsg({ type: "error", text: "Action failed" });
    }
  };

  const remove = async (user) => {
    if (!confirm(`Permanently delete "${user.username}"? This cannot be undone.`)) return;
    try {
      await adminApi.deleteUser(user.id);
      setUsers(u => u.filter(x => x.id !== user.id));
      setMsg({ type: "success", text: "User deleted" });
    } catch {
      setMsg({ type: "error", text: "Delete failed" });
    }
  };

  return (
    <div>
      <h2 style={{ marginBottom: 8, color: "#f1f5f9" }}>User Management</h2>
      <p style={{ color: "#94a3b8", marginBottom: 24, fontSize: "0.875rem" }}>
        View, search, suspend, or remove user accounts.
      </p>

      {msg && (
        <div style={{ ...S.card, background: msg.type === "success" ? "#16a34a22" : "#dc262622",
          color: msg.type === "success" ? "#4ade80" : "#f87171", marginBottom: 16 }}>
          {msg.text}
        </div>
      )}

      {/* Search bar */}
      <div style={S.card}>
        <form onSubmit={handleSearch} style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <input
            style={{ ...S.input, flex: 1, minWidth: 200 }}
            placeholder="Search by username or email…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <select
            style={{ ...S.input }}
            value={filter}
            onChange={e => setFilter(e.target.value)}
          >
            <option value="">All users</option>
            <option value="admin">Admins only</option>
            <option value="suspended">Suspended only</option>
          </select>
          <button type="submit" style={{ ...S.btn(), padding: "8px 18px" }}>
            Search
          </button>
          <button type="button" onClick={() => { setSearch(""); setFilter(""); load("", ""); }}
            style={{ ...S.btn("#94a3b8"), padding: "8px 18px" }}>
            Clear
          </button>
        </form>
      </div>

      {/* Table */}
      <div style={{ ...S.card, padding: 0, overflow: "auto" }}>
        {loading ? (
          <div style={{ padding: 24, textAlign: "center", color: "#94a3b8" }}>Loading…</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#0f172a" }}>
                {["ID", "Username", "Email", "Role", "Status", "Sessions",
                  "Points", "Joined", "Actions"].map(h => (
                  <th key={h} style={S.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr><td colSpan={9} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>
                  No users found
                </td></tr>
              ) : users.map(u => (
                <tr key={u.id} style={{ background: u.is_suspended ? "#450a0a22" : "transparent" }}>
                  <td style={S.td}>{u.id}</td>
                  <td style={S.td}><strong>{u.username}</strong></td>
                  <td style={{ ...S.td, color: "#94a3b8", fontSize: "0.8rem" }}>{u.email}</td>
                  <td style={S.td}>
                    <span style={S.badge(u.role === "admin" ? "#f59e0b" : "#60a5fa")}>
                      {u.role}
                    </span>
                  </td>
                  <td style={S.td}>
                    <span style={S.badge(u.is_suspended ? "#ef4444" : "#22c55e")}>
                      {u.is_suspended ? "Suspended" : "Active"}
                    </span>
                  </td>
                  <td style={S.td}>{u.session_count}</td>
                  <td style={S.td}>{u.total_points}</td>
                  <td style={{ ...S.td, fontSize: "0.78rem", color: "#94a3b8" }}>
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td style={{ ...S.td, display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <button onClick={() => suspend(u)}
                      style={S.btn(u.is_suspended ? "#22c55e" : "#f59e0b")}>
                      {u.is_suspended ? "Unsuspend" : "Suspend"}
                    </button>
                    <button onClick={() => promote(u)}
                      style={S.btn(u.role === "admin" ? "#94a3b8" : "#a78bfa")}>
                      {u.role === "admin" ? "Demote" : "Make Admin"}
                    </button>
                    <button onClick={() => remove(u)} style={S.btn("#ef4444")}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <p style={{ fontSize: "0.75rem", color: "#475569" }}>
        Showing {users.length} user(s)
      </p>
    </div>
  );
}
