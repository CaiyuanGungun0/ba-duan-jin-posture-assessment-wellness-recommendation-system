import { useEffect, useState } from "react";
import { notificationsApi } from "../services/api.js";

const TYPE_ICONS = {
  achievement: "🏆",
  streak: "🔥",
  reminder: "⏰",
  social: "👥",
  report: "📊",
  points: "⭐",
};

export default function Notifications() {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    const r = await notificationsApi.list(30);
    setNotifications(r.data);
    setLoading(false);
  };

  useEffect(() => { refresh(); }, []);

  const handleMarkRead = async (id) => {
    await notificationsApi.markRead(id);
    refresh();
  };

  const handleMarkAll = async () => {
    await notificationsApi.markAllRead();
    refresh();
  };

  if (loading) return <div className="spinner" />;

  const unread = notifications.filter(n => !n.read_flag).length;

  return (
    <div className="page-container">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1>Notifications {unread > 0 && <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>({unread} unread)</span>}</h1>
        {unread > 0 && (
          <button className="btn btn-outline" onClick={handleMarkAll} style={{ fontSize: "0.82rem" }}>
            Mark all as read
          </button>
        )}
      </div>

      {notifications.length === 0 ? (
        <div className="empty-state"><p>No notifications yet</p></div>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          {notifications.map((n, i) => (
            <div
              key={n.id}
              style={{
                display: "flex", gap: 12, alignItems: "flex-start", padding: "14px 20px",
                borderBottom: i < notifications.length - 1 ? "1px solid var(--beige-200)" : "none",
                background: n.read_flag ? "#fff" : "var(--green-50)",
                cursor: n.read_flag ? "default" : "pointer",
              }}
              onClick={() => !n.read_flag && handleMarkRead(n.id)}
            >
              <span style={{ fontSize: "1.3rem", flexShrink: 0 }}>{TYPE_ICONS[n.type] || "📢"}</span>
              <div style={{ flex: 1 }}>
                <p style={{ fontSize: "0.88rem", color: "var(--text-primary)", marginBottom: 2 }}>{n.content}</p>
                <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  {new Date(n.created_at).toLocaleString()}
                </p>
              </div>
              {!n.read_flag && (
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--green-500)", marginTop: 6, flexShrink: 0 }} />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
