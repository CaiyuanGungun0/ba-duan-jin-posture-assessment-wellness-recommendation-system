import { useEffect, useState } from "react";
import { socialApi } from "../services/api.js";
import { useAuth } from "../services/auth.jsx";

const POST_TYPE_ICONS = {
  session: "🧘",
  achievement: "🏆",
  streak: "🔥",
  weekly_summary: "📊",
};

export default function Social() {
  const { user } = useAuth();
  const [tab, setTab] = useState("feed");
  const [feed, setFeed] = useState([]);
  const [explore, setExplore] = useState([]);
  const [followers, setFollowers] = useState([]);
  const [following, setFollowing] = useState([]);
  const [loading, setLoading] = useState(true);
  const [postForm, setPostForm] = useState({ caption: "", post_type: "session" });
  const [posting, setPosting] = useState(false);

  const refresh = async () => {
    const [feedR, exploreR, followersR, followingR] = await Promise.all([
      socialApi.feed(),
      socialApi.explore(),
      socialApi.followers(),
      socialApi.following(),
    ]);
    setFeed(feedR.data);
    setExplore(exploreR.data);
    setFollowers(followersR.data);
    setFollowing(followingR.data);
    setLoading(false);
  };

  useEffect(() => { refresh(); }, []);

  const handlePost = async (e) => {
    e.preventDefault();
    setPosting(true);
    try {
      await socialApi.createPost(postForm);
      setPostForm({ caption: "", post_type: "session" });
      refresh();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to post");
    } finally {
      setPosting(false);
    }
  };

  const handleLike = async (postId) => {
    await socialApi.likePost(postId);
    refresh();
  };

  const handleDelete = async (postId) => {
    if (!confirm("Delete this post?")) return;
    await socialApi.deletePost(postId);
    refresh();
  };

  const handleFollow = async (userId) => {
    try {
      await socialApi.follow(userId);
      refresh();
    } catch {}
  };

  const handleUnfollow = async (userId) => {
    await socialApi.unfollow(userId);
    refresh();
  };

  const followingIds = new Set(following.map(f => f.user_id));

  const PostCard = ({ post }) => (
    <div className="card" style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
        <img
          src={post.profile_photo ? `http://localhost:8000${post.profile_photo}` : `https://ui-avatars.com/api/?name=${post.username}&size=36&background=4a7c59&color=fff`}
          alt="" style={{ width: 36, height: 36, borderRadius: "50%", objectFit: "cover" }}
        />
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{post.username}</div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
            {new Date(post.created_at).toLocaleDateString()}
          </div>
        </div>
        <span style={{ fontSize: "1.4rem" }}>{POST_TYPE_ICONS[post.post_type] || "📝"}</span>
      </div>
      {post.caption && <p style={{ fontSize: "0.9rem", marginBottom: 10 }}>{post.caption}</p>}
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={() => handleLike(post.id)}
          className="btn btn-outline" style={{ fontSize: "0.8rem", padding: "5px 12px" }}>
          ❤️ {post.likes}
        </button>
        {post.username === user?.username && (
          <button onClick={() => handleDelete(post.id)}
            style={{ background: "none", border: "none", color: "#e05252", cursor: "pointer", fontSize: "0.8rem" }}>
            Delete
          </button>
        )}
      </div>
    </div>
  );

  if (loading) return <div className="spinner" />;

  return (
    <div className="page-container">
      <h1 style={{ marginBottom: 8 }}>Community</h1>
      <p style={{ color: "var(--text-muted)", marginBottom: 24 }}>Share your progress and connect with fellow practitioners</p>

      <div style={{ display: "flex", gap: 8, marginBottom: 24, flexWrap: "wrap" }}>
        {["feed", "explore", "connections"].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={tab === t ? "btn btn-primary" : "btn btn-outline"}
            style={{ textTransform: "capitalize" }}>
            {t === "feed" ? `My Feed (${feed.length})` : t === "explore" ? "Explore" : `Connections (${followers.length + following.length})`}
          </button>
        ))}
      </div>

      {/* Create post */}
      {(tab === "feed") && user?.allow_social_sharing && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h3 style={{ marginBottom: 12 }}>Share with Community</h3>
          <form onSubmit={handlePost}>
            <div className="form-group">
              <label>Post Type</label>
              <select className="form-select" value={postForm.post_type}
                onChange={e => setPostForm(f => ({ ...f, post_type: e.target.value }))}>
                <option value="session">🧘 Session Completion</option>
                <option value="achievement">🏆 Achievement</option>
                <option value="streak">🔥 Streak Milestone</option>
                <option value="weekly_summary">📊 Weekly Summary</option>
              </select>
            </div>
            <div className="form-group">
              <label>Caption</label>
              <input value={postForm.caption}
                onChange={e => setPostForm(f => ({ ...f, caption: e.target.value }))}
                placeholder="Share your experience…" />
            </div>
            <button className="btn btn-primary" type="submit" disabled={posting}>
              {posting ? "Posting…" : "Share Post"}
            </button>
          </form>
        </div>
      )}

      {tab === "feed" && (
        feed.length === 0
          ? <div className="empty-state"><p>Your feed is empty. Follow other practitioners to see their updates!</p></div>
          : feed.map(p => <PostCard key={p.id} post={p} />)
      )}

      {tab === "explore" && (
        explore.length === 0
          ? <div className="empty-state"><p>No public posts yet. Be the first to share!</p></div>
          : explore.map(p => <PostCard key={p.id} post={p} />)
      )}

      {tab === "connections" && (
        <div className="grid-2" style={{ gap: 20 }}>
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Following ({following.length})</h3>
            {following.length === 0
              ? <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Not following anyone yet</p>
              : following.map(u => (
                <div key={u.user_id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--beige-200)" }}>
                  <img src={u.profile_photo ? `http://localhost:8000${u.profile_photo}` : `https://ui-avatars.com/api/?name=${u.username}&size=32&background=4a7c59&color=fff`}
                    alt="" style={{ width: 32, height: 32, borderRadius: "50%" }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500, fontSize: "0.85rem" }}>{u.username}</div>
                    <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>{u.level} · {u.total_points} pts</div>
                  </div>
                  <button onClick={() => handleUnfollow(u.user_id)}
                    className="btn btn-outline" style={{ fontSize: "0.75rem", padding: "3px 10px" }}>
                    Unfollow
                  </button>
                </div>
              ))
            }
          </div>
          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Followers ({followers.length})</h3>
            {followers.length === 0
              ? <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>No followers yet</p>
              : followers.map(u => (
                <div key={u.user_id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--beige-200)" }}>
                  <img src={u.profile_photo ? `http://localhost:8000${u.profile_photo}` : `https://ui-avatars.com/api/?name=${u.username}&size=32&background=4a7c59&color=fff`}
                    alt="" style={{ width: 32, height: 32, borderRadius: "50%" }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500, fontSize: "0.85rem" }}>{u.username}</div>
                    <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>{u.level} · {u.total_points} pts</div>
                  </div>
                  {!followingIds.has(u.user_id) && (
                    <button onClick={() => handleFollow(u.user_id)}
                      className="btn btn-primary" style={{ fontSize: "0.75rem", padding: "3px 10px" }}>
                      Follow Back
                    </button>
                  )}
                </div>
              ))
            }
          </div>
        </div>
      )}
    </div>
  );
}
