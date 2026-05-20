import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../../services/auth.jsx";

const NAV = [
  { to: "/admin/users",    label: "User Management",     icon: "👥" },
  { to: "/admin/sessions", label: "Session Monitoring",  icon: "📋" },
  { to: "/admin/rules",    label: "Recommendation Rules",icon: "📝" },
  { to: "/admin/dataset",  label: "Dataset Oversight",   icon: "🗄️" },
  { to: "/admin/reports",  label: "Reports",             icon: "📊" },
];

export default function AdminLayout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => { logout(); navigate("/login"); };

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#0f172a" }}>
      {/* Sidebar */}
      <aside style={{
        width: 240, background: "#1e293b", display: "flex",
        flexDirection: "column", padding: "24px 0", flexShrink: 0,
        borderRight: "1px solid #334155",
      }}>
        <div style={{ padding: "0 20px 24px", borderBottom: "1px solid #334155" }}>
          <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#f1f5f9" }}>
            Admin Portal
          </div>
          <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: 4 }}>
            {user?.username}
          </div>
        </div>

        <nav style={{ flex: 1, padding: "16px 12px" }}>
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to} to={to}
              style={({ isActive }) => ({
                display: "flex", alignItems: "center", gap: 10,
                padding: "10px 12px", borderRadius: 8, marginBottom: 4,
                textDecoration: "none", fontSize: "0.875rem",
                background: isActive ? "#3b82f620" : "transparent",
                color: isActive ? "#60a5fa" : "#94a3b8",
                fontWeight: isActive ? 600 : 400,
                transition: "all 0.15s",
              })}
            >
              <span>{icon}</span>{label}
            </NavLink>
          ))}
        </nav>

        <div style={{ padding: "16px 20px", borderTop: "1px solid #334155" }}>
          <NavLink to="/" style={{ display: "block", color: "#94a3b8", fontSize: "0.8rem",
            textDecoration: "none", marginBottom: 8 }}>
            ← Back to App
          </NavLink>
          <button onClick={handleLogout} style={{
            background: "none", border: "1px solid #475569", color: "#94a3b8",
            padding: "6px 12px", borderRadius: 6, cursor: "pointer",
            fontSize: "0.8rem", width: "100%",
          }}>
            Logout
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, padding: 32, color: "#f1f5f9", overflowY: "auto" }}>
        {children}
      </main>
    </div>
  );
}
