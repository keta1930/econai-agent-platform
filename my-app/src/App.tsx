import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { RequireAuth } from "@/components/guards/RequireAuth";
import { StudentLayout } from "@/components/layouts/StudentLayout";
import { AdminLayout } from "@/components/layouts/AdminLayout";
import LoginPage from "@/pages/auth/LoginPage";
import RegisterPage from "@/pages/auth/RegisterPage";
import StudentTaskListPage from "@/pages/student/TaskListPage";
import StudentTaskDetailPage from "@/pages/student/TaskDetailPage";
import GradesPage from "@/pages/student/GradesPage";
import DashboardPage from "@/pages/admin/DashboardPage";
import CreateTaskPage from "@/pages/admin/CreateTaskPage";
import AdminTaskDetailPage from "@/pages/admin/TaskDetailPage";
import StudentDetailPage from "@/pages/admin/StudentDetailPage";
import SubmissionDetailPage from "@/pages/admin/SubmissionDetailPage";
import RosterPage from "@/pages/admin/RosterPage";
import ModelsPage from "@/pages/admin/ModelsPage";

function RootRedirect() {
  const { isAuthenticated, role } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Navigate to={role === "admin" ? "/admin/dashboard" : "/student/tasks"} replace />;
}

export default function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Student routes */}
      <Route
        path="/student"
        element={
          <RequireAuth role="student">
            <StudentLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="tasks" replace />} />
        <Route path="tasks" element={<StudentTaskListPage />} />
        <Route path="tasks/:taskId" element={<StudentTaskDetailPage />} />
        <Route path="grades" element={<GradesPage />} />
      </Route>

      {/* Admin routes */}
      <Route
        path="/admin"
        element={
          <RequireAuth role="admin">
            <AdminLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="tasks/new" element={<CreateTaskPage />} />
        <Route path="tasks/:taskId" element={<AdminTaskDetailPage />} />
        <Route path="tasks/:taskId/submissions/:studentId" element={<SubmissionDetailPage />} />
        <Route path="students/:studentId" element={<StudentDetailPage />} />
        <Route path="roster" element={<RosterPage />} />
        <Route path="models" element={<ModelsPage />} />
      </Route>

      {/* Root redirect */}
      <Route path="/" element={<RootRedirect />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
