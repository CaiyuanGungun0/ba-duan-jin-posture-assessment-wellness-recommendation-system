import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import Achievements from "./pages/Achievements";
import Dashboard from "./pages/Dashboard";
import ExerciseLibrary from "./pages/ExerciseLibrary";
import Login from "./pages/Login";
import Notifications from "./pages/Notifications";
import Profile from "./pages/Profile";
import Register from "./pages/Register";
import Reports from "./pages/Reports";
import Session from "./pages/Session";
import Social from "./pages/Social";
import Wellness from "./pages/Wellness";
import AdminLayout from "./pages/admin/AdminLayout";
import AdminUserManagement from "./pages/admin/AdminUserManagement";
import AdminSessionMonitoring from "./pages/admin/AdminSessionMonitoring";
import AdminRecommendationRules from "./pages/admin/AdminRecommendationRules";
import AdminDataset from "./pages/admin/AdminDataset";
import AdminReports from "./pages/admin/AdminReports";
import { AuthProvider, useAuth } from "./services/auth.jsx";

function PrivateRoute({ children }) {
  const { token } = useAuth();
  return token ? children : <Navigate to="/login" replace />;
}

function AdminRoute({ children }) {
  const { token, user } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  if (user && user.role !== "admin") return <Navigate to="/" replace />;
  if (!user) return null; // still loading
  return children;
}

function PrivateLayout({ children }) {
  return (
    <PrivateRoute>
      <Navbar />
      <main>{children}</main>
    </PrivateRoute>
  );
}

function AdminPageLayout({ children }) {
  return (
    <AdminRoute>
      <AdminLayout>{children}</AdminLayout>
    </AdminRoute>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* User routes */}
          <Route path="/" element={<PrivateLayout><Dashboard /></PrivateLayout>} />
          <Route path="/session" element={<PrivateLayout><Session /></PrivateLayout>} />
          <Route path="/profile" element={<PrivateLayout><Profile /></PrivateLayout>} />
          <Route path="/wellness" element={<PrivateLayout><Wellness /></PrivateLayout>} />
          <Route path="/achievements" element={<PrivateLayout><Achievements /></PrivateLayout>} />
          <Route path="/social" element={<PrivateLayout><Social /></PrivateLayout>} />
          <Route path="/exercises" element={<PrivateLayout><ExerciseLibrary /></PrivateLayout>} />
          <Route path="/reports" element={<PrivateLayout><Reports /></PrivateLayout>} />
          <Route path="/notifications" element={<PrivateLayout><Notifications /></PrivateLayout>} />

          {/* Admin routes */}
          <Route path="/admin/users" element={<AdminPageLayout><AdminUserManagement /></AdminPageLayout>} />
          <Route path="/admin/sessions" element={<AdminPageLayout><AdminSessionMonitoring /></AdminPageLayout>} />
          <Route path="/admin/rules" element={<AdminPageLayout><AdminRecommendationRules /></AdminPageLayout>} />
          <Route path="/admin/dataset" element={<AdminPageLayout><AdminDataset /></AdminPageLayout>} />
          <Route path="/admin/reports" element={<AdminPageLayout><AdminReports /></AdminPageLayout>} />
          <Route path="/admin" element={<Navigate to="/admin/users" replace />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
