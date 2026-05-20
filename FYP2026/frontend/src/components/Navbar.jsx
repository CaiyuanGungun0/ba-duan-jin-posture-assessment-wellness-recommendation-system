import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { notificationsApi } from "../services/api.js";
import { useAuth } from "../services/auth.jsx";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!user) return;
    notificationsApi.unreadCount()
      .then(r => setUnread(r.data.unread_count))
      .catch(() => {});
    const id = setInterval(() => {
      notificationsApi.unreadCount()
        .then(r => setUnread(r.data.unread_count))
        .catch(() => {});
    }, 60000);
    return () => clearInterval(id);
  }, [user]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const LEVEL_COLORS = { Bronze: "#cd7f32", Silver: "#9e9e9e", Gold: "#ffc107", Platinum: "#7b68ee" };

  return (
    <nav className="navbar">
      <span className="navbar-logo">八段锦 Wellness</span>
      <div className="navbar-nav">
        <NavLink to="/" end>Dashboard</NavLink>
        <NavLink to="/exercises">Library</NavLink>
        <NavLink to="/session">Practice</NavLink>
        <NavLink to="/wellness">Wellness</NavLink>
        <NavLink to="/achievements">Achievements</NavLink>
        <NavLink to="/social">Community</NavLink>
        <NavLink to="/reports">Reports</NavLink>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {/* Notification bell */}
        <NavLink to="/notifications" style={{ position: "relative", textDecoration: "none" }}>
          <span style={{ fontSize: "1.1rem" }}>🔔</span>
          {unread > 0 && (
            <span style={{
              position: "absolute", top: -4, right: -6,
              background: "#e05252", color: "#fff",
              borderRadius: "50%", width: 16, height: 16,
              fontSize: "0.65rem", display: "flex", alignItems: "center", justifyContent: "center",
              fontWeight: 700,
            }}>
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </NavLink>

        {/* User avatar + menu */}
        <div style={{ position: "relative" }}>
          <button
            onClick={() => setMenuOpen(o => !o)}
            style={{
              display: "flex", alignItems: "center", gap: 8,
              background: "none", border: "none", cursor: "pointer",
              padding: "4px 8px", borderRadius: 8,
            }}
          >
            <img
              src={user?.profile_photo
                ? `http://localhost:8000${user.profile_photo}`
                : `https://ui-avatars.com/api/?name=${user?.username || "U"}&size=32&background=4a7c59&color=fff`}
              alt="" style={{ width: 32, height: 32, borderRadius: "50%", objectFit: "cover" }}
            />
            <span style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>{user?.username}</span>
            {user?.level && (
              <span style={{ fontSize: "0.7rem", fontWeight: 600, color: LEVEL_COLORS[user.level] }}>
                {user.level}
              </span>
            )}
          </button>

          {menuOpen && (
            <div style={{
              position: "absolute", right: 0, top: "calc(100% + 8px)",
              background: "#fff", borderRadius: 12, boxShadow: "0 4px 20px rgba(0,0,0,0.12)",
              minWidth: 160, zIndex: 200, overflow: "hidden",
            }}
              onMouseLeave={() => setMenuOpen(false)}
            >
              {[
                { to: "/profile", label: "👤 My Profile" },
                { to: "/achievements", label: "🏆 Achievements" },
                { to: "/wellness", label: "💚 Wellness" },
                { to: "/reports", label: "📊 Health Reports" },
              ].map(item => (
                <NavLink key={item.to} to={item.to}
                  onClick={() => setMenuOpen(false)}
                  style={{
                    display: "block", padding: "10px 16px",
                    textDecoration: "none", fontSize: "0.85rem", color: "var(--text-primary)",
                  }}
                  className="navbar-dropdown-item"
                >
                  {item.label}
                </NavLink>
              ))}
              <div style={{ borderTop: "1px solid var(--beige-200)" }} />
              <button
                onClick={handleLogout}
                style={{
                  width: "100%", padding: "10px 16px", background: "none", border: "none",
                  textAlign: "left", cursor: "pointer", fontSize: "0.85rem", color: "#e05252",
                }}
              >
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
