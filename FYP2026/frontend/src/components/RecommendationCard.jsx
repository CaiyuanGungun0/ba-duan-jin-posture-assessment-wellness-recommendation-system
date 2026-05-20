import { useState } from "react";
import { recommendationsApi } from "../services/api";

export default function RecommendationCard({ recommendation: initial }) {
  const [text, setText] = useState(initial);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const res = await recommendationsApi.generate(true);
      setText(res.data.content);
    } catch {
      /* silently skip */
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card" style={{ borderLeft: "4px solid var(--green-400)", flex: 1 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <p className="section-title" style={{ marginBottom: 0 }}>Daily Recommendation</p>
        <button
          className="btn btn-outline"
          style={{ padding: "3px 10px", fontSize: "0.78rem" }}
          onClick={refresh}
          disabled={loading}
        >
          {loading ? "…" : "Refresh"}
        </button>
      </div>
      {text ? (
        <p style={{ fontSize: "0.88rem", color: "var(--text-secondary)", lineHeight: 1.7 }}>{text}</p>
      ) : (
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", fontStyle: "italic" }}>
          Complete a session to receive your personalised recommendation.
        </p>
      )}
    </div>
  );
}
