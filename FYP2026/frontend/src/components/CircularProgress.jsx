export default function CircularProgress({ value = 0, size = 100, strokeWidth = 8, label = "" }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(Math.max(value, 0), 100) / 100) * circumference;

  const color =
    value >= 80 ? "#4a7c59" :
    value >= 60 ? "#c8a830" : "#e05252";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke="#e8f0ea" strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={color} strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
        <text
          x="50%" y="50%"
          dominantBaseline="middle" textAnchor="middle"
          fill={color}
          style={{ transform: "rotate(90deg)", transformOrigin: "50% 50%", fontSize: size * 0.22, fontWeight: 600 }}
        >
          {value > 0 ? `${Math.round(value)}%` : "—"}
        </text>
      </svg>
      {label && (
        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 500 }}>{label}</span>
      )}
    </div>
  );
}
