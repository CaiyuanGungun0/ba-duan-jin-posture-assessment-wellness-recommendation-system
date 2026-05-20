import { useEffect, useState } from "react";
import { gamificationApi } from "../services/api.js";

const LEVEL_COLORS = { Bronze: "#cd7f32", Silver: "#9e9e9e", Gold: "#ffc107", Platinum: "#7b68ee" };
const LEVEL_ORDER = ["Bronze", "Silver", "Gold", "Platinum"];
const LEVEL_POINTS = { Bronze: 0, Silver: 500, Gold: 1500, Platinum: 3000 };

export default function Achievements() {
  const [allAchievements, setAllAchievements] = useState([]);
  const [myAchievements, setMyAchievements] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [myRank, setMyRank] = useState(null);
  const [tab, setTab] = useState("badges");
  const [checking, setChecking] = useState(false);
  const [newBadges, setNewBadges] = useState([]);

  useEffect(() => {
    Promise.all([
      gamificationApi.all(),
      gamificationApi.mine(),
      gamificationApi.leaderboard(10),
      gamificationApi.myRank(),
    ]).then(([all, mine, lb, rank]) => {
      setAllAchievements(all.data);
      setMyAchievements(mine.data);
      setLeaderboard(lb.data);
      setMyRank(rank.data);
    });
  }, []);

  const handleCheckAchievements = async () => {
    setChecking(true);
    try {
      const r = await gamificationApi.check();
      setNewBadges(r.data);
      const [mine, rank] = await Promise.all([gamificationApi.mine(), gamificationApi.myRank()]);
      setMyAchievements(mine.data);
      setMyRank(rank.data);
    } finally {
      setChecking(false);
    }
  };

  const earnedIds = new Set(myAchievements.map(a => a.achievement.id));
  const totalEarned = myAchievements.length;
  const totalPoints = myAchievements.reduce((s, a) => s + a.achievement.points, 0);

  const currentLevel = myRank?.level || "Bronze";
  const levelIdx = LEVEL_ORDER.indexOf(currentLevel);
  const nextLevel = LEVEL_ORDER[levelIdx + 1];
  const currentPoints = myRank?.total_points || 0;
  const nextLevelPoints = nextLevel ? LEVEL_POINTS[nextLevel] : currentPoints;
  const levelProgress = nextLevel
    ? Math.min(100, Math.round((currentPoints - LEVEL_POINTS[currentLevel]) / (nextLevelPoints - LEVEL_POINTS[currentLevel]) * 100))
    : 100;

  return (
    <div className="page-container">
      <h1 style={{ marginBottom: 8 }}>Achievements</h1>
      <p style={{ color: "var(--text-muted)", marginBottom: 24 }}>Earn badges, climb levels, and compete on the leaderboard</p>

      {/* Level progress */}
      {myRank && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div>
              <span style={{ fontSize: "1.8rem", fontWeight: 700, color: LEVEL_COLORS[currentLevel] }}>
                {currentLevel}
              </span>
              {nextLevel && (
                <span style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginLeft: 12 }}>
                  → {nextLevel} ({nextLevelPoints - currentPoints} pts needed)
                </span>
              )}
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "1.4rem", fontWeight: 600, color: "var(--green-700)" }}>{currentPoints.toLocaleString()} pts</div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Rank #{myRank.rank}</div>
            </div>
          </div>
          <div style={{ height: 10, background: "var(--beige-200)", borderRadius: 5 }}>
            <div style={{
              height: "100%", borderRadius: 5,
              background: `linear-gradient(90deg, ${LEVEL_COLORS[currentLevel]}, ${LEVEL_COLORS[nextLevel || currentLevel]})`,
              width: `${levelProgress}%`, transition: "width 0.5s",
            }} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontSize: "0.75rem", color: "var(--text-muted)" }}>
            <span>{LEVEL_POINTS[currentLevel]} pts</span>
            <span>{nextLevel ? `${nextLevelPoints} pts` : "MAX LEVEL 🏆"}</span>
          </div>
        </div>
      )}

      {/* Tab selector */}
      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        {["badges", "leaderboard"].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={tab === t ? "btn btn-primary" : "btn btn-outline"}
            style={{ textTransform: "capitalize" }}>
            {t === "badges" ? `Badges (${totalEarned}/${allAchievements.length})` : "Leaderboard"}
          </button>
        ))}
        <button className="btn btn-outline" onClick={handleCheckAchievements} disabled={checking}
          style={{ marginLeft: "auto" }}>
          {checking ? "Checking…" : "Check New Badges"}
        </button>
      </div>

      {/* New badges toast */}
      {newBadges.length > 0 && (
        <div style={{
          background: "var(--green-50)", border: "1px solid var(--green-300)",
          borderRadius: 12, padding: "12px 16px", marginBottom: 16,
        }}>
          <p style={{ fontWeight: 600, color: "var(--green-700)", marginBottom: 8 }}>
            🎉 You earned {newBadges.length} new badge{newBadges.length > 1 ? "s" : ""}!
          </p>
          {newBadges.map(b => (
            <span key={b.id} style={{
              display: "inline-flex", gap: 6, alignItems: "center",
              background: "#fff", borderRadius: 20, padding: "4px 12px",
              marginRight: 8, fontSize: "0.85rem", border: "1px solid var(--green-300)",
            }}>
              {b.badge_icon} {b.title}
            </span>
          ))}
        </div>
      )}

      {tab === "badges" && (
        <div className="achievement-grid">
          {allAchievements.map(a => {
            const earned = earnedIds.has(a.id);
            const earnedRecord = myAchievements.find(ua => ua.achievement.id === a.id);
            return (
              <div key={a.id} className={`achievement-card ${earned ? "earned" : "locked"}`}>
                <div style={{ fontSize: "2rem", marginBottom: 8, filter: earned ? "none" : "grayscale(1)" }}>
                  {a.badge_icon}
                </div>
                <div style={{ fontWeight: 600, fontSize: "0.9rem", marginBottom: 4 }}>{a.title}</div>
                <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: 8 }}>{a.description}</div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--green-600)" }}>
                    +{a.points} pts
                  </span>
                  {earned ? (
                    <span style={{ fontSize: "0.7rem", color: "var(--green-500)" }}>
                      ✓ {earnedRecord?.earned_at ? new Date(earnedRecord.earned_at).toLocaleDateString() : "Earned"}
                    </span>
                  ) : (
                    <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>🔒 Locked</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {tab === "leaderboard" && (
        <div className="card">
          <p className="section-title">Top 10 Players</p>
          {leaderboard.map((entry, i) => (
            <div key={entry.user_id} style={{
              display: "flex", alignItems: "center", gap: 14, padding: "12px 0",
              borderBottom: i < leaderboard.length - 1 ? "1px solid var(--beige-200)" : "none",
            }}>
              <span style={{
                width: 28, height: 28, borderRadius: "50%", display: "flex", alignItems: "center",
                justifyContent: "center", fontWeight: 700, fontSize: "0.85rem",
                background: i === 0 ? "#ffd700" : i === 1 ? "#c0c0c0" : i === 2 ? "#cd7f32" : "var(--beige-200)",
                color: i < 3 ? "#fff" : "var(--text-secondary)",
              }}>
                {i + 1}
              </span>
              <img
                src={entry.profile_photo ? `http://localhost:8000${entry.profile_photo}` : `https://ui-avatars.com/api/?name=${entry.username}&size=36&background=4a7c59&color=fff`}
                alt="" style={{ width: 36, height: 36, borderRadius: "50%", objectFit: "cover" }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 500, fontSize: "0.9rem" }}>{entry.username}</div>
                <div style={{ fontSize: "0.75rem", color: LEVEL_COLORS[entry.level] }}>{entry.level}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontWeight: 600, color: "var(--green-700)" }}>{entry.total_points.toLocaleString()} pts</div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>🔥 {entry.streak_days}d</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
