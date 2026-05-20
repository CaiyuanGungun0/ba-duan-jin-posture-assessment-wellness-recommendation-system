import axios from "axios";

const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("token");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;

export const authApi = {
  login: (data) => api.post("/auth/login", data),
  register: (data) => api.post("/auth/register", data),
  me: () => api.get("/auth/me"),
  updateProfile: (data) => api.patch("/auth/me", data),
};

export const profileApi = {
  get: () => api.get("/profile/"),
  update: (data) => api.patch("/profile/", data),
  changePassword: (data) => api.post("/profile/change-password", data),
  stats: () => api.get("/profile/stats"),
};

export const sessionsApi = {
  create: (data) => api.post("/sessions/", data),
  list: (limit = 20, session_type = null) =>
    api.get("/sessions/", { params: { limit, ...(session_type && { session_type }) } }),
  get: (id) => api.get(`/sessions/${id}`),
  getActions: (id) => api.get(`/sessions/${id}/actions`),
  delete: (id) => api.delete(`/sessions/${id}`),
};

export const dashboardApi = {
  summary: () => api.get("/dashboard/"),
};

export const recommendationsApi = {
  generate: (force = false) =>
    api.post("/recommendations/generate", { force_refresh: force }),
  list: () => api.get("/recommendations/"),
};

export const wellnessApi = {
  upsertHealthLog: (data) => api.post("/wellness/health-log", data),
  listHealthLog: (days = 30) => api.get("/wellness/health-log", { params: { days } }),
  todayHealthLog: () => api.get("/wellness/health-log/today"),
  addFood: (data) => api.post("/wellness/food-log", data),
  listFood: (days = 7) => api.get("/wellness/food-log", { params: { days } }),
  deleteFood: (id) => api.delete(`/wellness/food-log/${id}`),
  addWater: (amount_ml) => api.post("/wellness/water-log", { amount_ml }),
  todayWater: () => api.get("/wellness/water-log/today"),
  summary: (days = 7) => api.get("/wellness/summary", { params: { days } }),
};

export const gamificationApi = {
  all: () => api.get("/gamification/achievements"),
  mine: () => api.get("/gamification/my-achievements"),
  check: () => api.post("/gamification/check-achievements"),
  leaderboard: (limit = 20) => api.get("/gamification/leaderboard", { params: { limit } }),
  myRank: () => api.get("/gamification/my-rank"),
};

export const socialApi = {
  createPost: (data) => api.post("/social/posts", data),
  feed: (limit = 20) => api.get("/social/feed", { params: { limit } }),
  explore: (limit = 30) => api.get("/social/explore", { params: { limit } }),
  likePost: (id) => api.post(`/social/posts/${id}/like`),
  deletePost: (id) => api.delete(`/social/posts/${id}`),
  follow: (userId) => api.post(`/social/follow/${userId}`),
  unfollow: (userId) => api.delete(`/social/follow/${userId}`),
  followers: () => api.get("/social/followers"),
  following: () => api.get("/social/following"),
  addFavorite: (exerciseId) => api.post(`/social/favorites/${exerciseId}`),
  removeFavorite: (exerciseId) => api.delete(`/social/favorites/${exerciseId}`),
  favorites: () => api.get("/social/favorites"),
};

export const notificationsApi = {
  list: (unreadOnly = false) => api.get("/notifications/", { params: { unread_only: unreadOnly } }),
  markRead: (id) => api.post(`/notifications/${id}/read`),
  markAllRead: () => api.post("/notifications/read-all"),
  unreadCount: () => api.get("/notifications/unread-count"),
};

export const reportsApi = {
  list: () => api.get("/reports/"),
  generate: () => api.post("/reports/generate"),
};

export const exerciseApi = {
  list: (category = null, difficulty = null) =>
    api.get("/exercises/", { params: { ...(category && { category }), ...(difficulty && { difficulty }) } }),
  get: (id) => api.get(`/exercises/${id}`),
};

export const poseApi = {
  analyzeVideo: (file, onUploadProgress) => {
    const fd = new FormData();
    fd.append("file", file);
    return api.post("/pose/analyze-video", fd, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress,
      timeout: 10 * 60 * 1000, // 10 min — long video can take time
    });
  },
};

export const adminApi = {
  // User management
  listUsers: (params = {}) => api.get("/admin/users", { params }),
  updateUser: (id, data) => api.patch(`/admin/users/${id}`, data),
  deleteUser: (id) => api.delete(`/admin/users/${id}`),

  // Session monitoring
  listSessions: (params = {}) => api.get("/admin/sessions", { params }),
  getSession: (id) => api.get(`/admin/sessions/${id}`),

  // Recommendation rules
  listRules: () => api.get("/admin/recommendation-rules"),
  createRule: (data) => api.post("/admin/recommendation-rules", data),
  updateRule: (id, data) => api.patch(`/admin/recommendation-rules/${id}`, data),
  deleteRule: (id) => api.delete(`/admin/recommendation-rules/${id}`),

  // Dataset oversight
  dataset: () => api.get("/admin/dataset"),
  logs: (lines = 100) => api.get("/admin/logs", { params: { lines } }),

  // Reports
  stats: () => api.get("/admin/stats"),
  accuracy: () => api.get("/admin/accuracy"),
  modelEval: () => api.get("/admin/model-eval"),
};
