import { useEffect, useState } from "react";
import { adminApi } from "../../services/api.js";

const S = {
  card: { background: "#1e293b", borderRadius: 10, padding: 20, marginBottom: 16,
    border: "1px solid #334155" },
  th: { padding: "10px 14px", textAlign: "left", fontSize: "0.75rem",
    color: "#94a3b8", fontWeight: 600, textTransform: "uppercase",
    borderBottom: "1px solid #334155" },
  td: { padding: "10px 14px", fontSize: "0.8rem", borderBottom: "1px solid #1e293b" },
  btn: (color = "#3b82f6") => ({
    padding: "7px 16px", borderRadius: 6, border: "none", cursor: "pointer",
    fontSize: "0.82rem", background: color + "22", color, fontWeight: 600,
  }),
  tab: (active) => ({
    padding: "8px 18px", borderRadius: 6, border: "none", cursor: "pointer",
    fontSize: "0.875rem", fontWeight: active ? 600 : 400,
    background: active ? "#3b82f620" : "transparent",
    color: active ? "#60a5fa" : "#94a3b8",
  }),
};

const EXT_COLORS = {
  csv: "#22c55e", mp4: "#a78bfa", avi: "#a78bfa", json: "#f59e0b",
  txt: "#94a3b8", npy: "#60a5fa", pkl: "#fb923c", h5: "#f43f5e",
};

function fmt(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function AdminDataset() {
  const [tab, setTab] = useState("dataset");
  const [data, setData] = useState(null);
  const [logs, setLogs] = useState(null);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [logLines, setLogLines] = useState(100);

  const loadDataset = async () => {
    setLoading(true);
    try {
      const r = await adminApi.dataset();
      setData(r.data);
    } finally {
      setLoading(false);
    }
  };

  const loadLogs = async () => {
    setLoading(true);
    try {
      const r = await adminApi.logs(logLines);
      setLogs(r.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (tab === "dataset") loadDataset();
    else loadLogs();
  }, [tab]);

  const files = data?.files?.filter(f =>
    !search || f.path.toLowerCase().includes(search.toLowerCase())
  ) || [];

  const extGroups = files.reduce((acc, f) => {
    acc[f.type] = (acc[f.type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      <h2 style={{ marginBottom: 8, color: "#f1f5f9" }}>Dataset Oversight</h2>
      <p style={{ color: "#94a3b8", marginBottom: 24, fontSize: "0.875rem" }}>
        Browse training samples in the data/ directory and monitor application logs.
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        <button style={S.tab(tab === "dataset")} onClick={() => setTab("dataset")}>
          Training Samples
        </button>
        <button style={S.tab(tab === "logs")} onClick={() => setTab("logs")}>
          System Logs
        </button>
      </div>

      {/* Dataset tab */}
      {tab === "dataset" && (
        <>
          {data && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(120px,1fr))",
              gap: 12, marginBottom: 20 }}>
              <div style={S.card}>
                <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f1f5f9" }}>
                  {data.total_files}
                </div>
                <div style={{ fontSize: "0.78rem", color: "#94a3b8" }}>Total Files</div>
              </div>
              {Object.entries(extGroups).map(([ext, count]) => (
                <div key={ext} style={S.card}>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700,
                    color: EXT_COLORS[ext] || "#94a3b8" }}>{count}</div>
                  <div style={{ fontSize: "0.78rem", color: "#94a3b8" }}>.{ext} files</div>
                </div>
              ))}
            </div>
          )}

          <div style={S.card}>
            <div style={{ display: "flex", gap: 10, marginBottom: 0 }}>
              <input
                style={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 6,
                  color: "#f1f5f9", padding: "8px 12px", fontSize: "0.875rem", flex: 1 }}
                placeholder="Filter by filename or path…"
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
              <button onClick={loadDataset} style={{ ...S.btn("#60a5fa"), padding: "8px 18px" }}>
                Refresh
              </button>
            </div>
          </div>

          <div style={{ ...S.card, padding: 0, overflow: "auto" }}>
            {loading ? (
              <div style={{ padding: 24, textAlign: "center", color: "#94a3b8" }}>Loading…</div>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "#0f172a" }}>
                    {["Filename", "Path", "Type", "Size", "Modified"].map(h => (
                      <th key={h} style={S.th}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {files.length === 0 ? (
                    <tr><td colSpan={5} style={{ ...S.td, textAlign: "center", color: "#64748b" }}>
                      {loading ? "Loading…" : "No files found"}
                    </td></tr>
                  ) : files.slice(0, 200).map((f, i) => (
                    <tr key={i}>
                      <td style={S.td}><strong style={{ color: "#f1f5f9" }}>{f.filename}</strong></td>
                      <td style={{ ...S.td, color: "#64748b", fontSize: "0.72rem",
                        maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis",
                        whiteSpace: "nowrap" }}>{f.path}</td>
                      <td style={S.td}>
                        <code style={{ background: "#0f172a",
                          color: EXT_COLORS[f.type] || "#94a3b8",
                          padding: "2px 6px", borderRadius: 4, fontSize: "0.72rem" }}>
                          .{f.type}
                        </code>
                      </td>
                      <td style={S.td}>{fmt(f.size_bytes)}</td>
                      <td style={{ ...S.td, color: "#64748b", fontSize: "0.72rem" }}>
                        {f.modified_at ? new Date(f.modified_at).toLocaleString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <p style={{ fontSize: "0.72rem", color: "#475569" }}>
            Showing up to 200 files from data/ directory.
          </p>
        </>
      )}

      {/* Logs tab */}
      {tab === "logs" && (
        <>
          <div style={S.card}>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <label style={{ color: "#94a3b8", fontSize: "0.875rem" }}>Lines to show:</label>
              <select
                value={logLines}
                onChange={e => setLogLines(Number(e.target.value))}
                style={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 6,
                  color: "#f1f5f9", padding: "6px 10px" }}>
                {[50, 100, 200, 500].map(n => (
                  <option key={n} value={n}>{n} lines</option>
                ))}
              </select>
              <button onClick={loadLogs} style={{ ...S.btn("#60a5fa"), padding: "8px 18px" }}>
                Reload
              </button>
              {logs && (
                <span style={{ color: "#64748b", fontSize: "0.78rem", marginLeft: "auto" }}>
                  {logs.log_file}
                </span>
              )}
            </div>
          </div>

          <div style={{ ...S.card, padding: 0 }}>
            {loading ? (
              <div style={{ padding: 24, textAlign: "center", color: "#94a3b8" }}>Loading…</div>
            ) : (
              <pre style={{
                margin: 0, padding: 20,
                fontFamily: "monospace", fontSize: "0.75rem",
                color: "#94a3b8", lineHeight: 1.6,
                maxHeight: 600, overflowY: "auto",
                background: "#0f172a",
              }}>
                {logs?.lines?.join("\n") || "No log entries."}
              </pre>
            )}
          </div>
        </>
      )}
    </div>
  );
}
