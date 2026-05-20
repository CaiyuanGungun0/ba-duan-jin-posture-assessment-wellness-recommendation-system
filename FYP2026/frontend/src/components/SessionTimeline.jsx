export default function SessionTimeline({ sessions = [] }) {
  if (!sessions.length) {
    return (
      <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
        No sessions yet. Start your first Ba Duan Jin practice!
      </p>
    );
  }

  const fmt = (iso) => {
    const d = new Date(iso);
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "short" }) +
      " · " + d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  };

  const fmtDur = (s) => {
    if (s < 60) return `${s}s`;
    return `${Math.floor(s / 60)}m ${s % 60}s`;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {sessions.map((s, i) => (
        <div
          key={s.id}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 14,
            padding: "12px 0",
            borderBottom: i < sessions.length - 1 ? "1px solid var(--beige-200)" : "none",
          }}
        >
          {/* Score dot */}
          <div style={{
            width: 42, height: 42, borderRadius: "50%",
            background: s.total_score >= 80 ? "var(--green-100)" :
                        s.total_score >= 60 ? "#fdf4d4" : "#fde8e8",
            color: s.total_score >= 80 ? "var(--green-700)" :
                   s.total_score >= 60 ? "#9a7a00" : "#c43c3c",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "0.8rem", fontWeight: 600, flexShrink: 0,
          }}>
            {s.total_score > 0 ? `${Math.round(s.total_score)}%` : "—"}
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontSize: "0.88rem", fontWeight: 500, color: "var(--text-primary)" }}>
              {fmt(s.date)}
            </p>
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
              {fmtDur(s.duration_seconds)} · {s.movement_count} movement{s.movement_count !== 1 ? "s" : ""}
            </p>
          </div>

          {s.notes && (
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", maxWidth: 160, textAlign: "right" }}>
              {s.notes}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
