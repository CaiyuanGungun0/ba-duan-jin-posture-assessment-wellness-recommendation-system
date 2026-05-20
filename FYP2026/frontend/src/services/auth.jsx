import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { authApi } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (token) {
      authApi.me().then((r) => setUser(r.data)).catch(() => logout());
    }
  }, [token]);

  const login = useCallback((tok) => {
    localStorage.setItem("token", tok);
    setToken(tok);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!token) return;
    try {
      const r = await authApi.me();
      setUser(r.data);
    } catch {}
  }, [token]);

  return (
    <AuthContext.Provider value={{ token, user, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
