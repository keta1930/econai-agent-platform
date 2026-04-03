import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { RequireAuth } from "@/components/guards/RequireAuth";
import { StudentLayout } from "@/components/layouts/StudentLayout";
import { AdminLayout } from "@/components/layouts/AdminLayout";
import { SuperAdminLayout } from "@/components/layouts/SuperAdminLayout";
import { ClassProvider } from "@/contexts/ClassContext";
import LoginPage from "@/pages/auth/LoginPage";
import RegisterPage from "@/pages/auth/RegisterPage";
import StudentTaskListPage from "@/pages/student/TaskListPage";
import StudentTaskDetailPage from "@/pages/student/TaskDetailPage";
import GradesPage from "@/pages/student/GradesPage";
import DashboardPage from "@/pages/admin/DashboardPage";
import ClassManagePage from "@/pages/admin/ClassManagePage";
import CreateTaskPage from "@/pages/admin/CreateTaskPage";
import AdminTaskDetailPage from "@/pages/admin/TaskDetailPage";
import StudentDetailPage from "@/pages/admin/StudentDetailPage";
import SubmissionDetailPage from "@/pages/admin/SubmissionDetailPage";
import RosterPage from "@/pages/admin/RosterPage";
import ModelsPage from "@/pages/admin/ModelsPage";
import SharingPage from "@/pages/student/SharingPage";
import SharingManagePage from "@/pages/admin/SharingManagePage";
import BackupManagePage from "@/pages/admin/BackupManagePage";
import AdminManagePage from "@/pages/super-admin/AdminManagePage";

function RootRedirect() {
  const { isAuthenticated, role } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (role === "super_admin") return <Navigate to="/super-admin/admins" replace />;
  if (role === "admin") return <Navigate to="/admin/dashboard" replace />;
  return <Navigate to="/student/tasks" replace />;
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
        <Route path="sharing" element={<SharingPage />} />
      </Route>

      {/* Admin routes */}
      <Route
        path="/admin"
        element={
          <RequireAuth role="admin">
            <ClassProvider>
              <AdminLayout />
            </ClassProvider>
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="classes" element={<ClassManagePage />} />
        <Route path="tasks/new" element={<CreateTaskPage />} />
        <Route path="tasks/:taskId" element={<AdminTaskDetailPage />} />
        <Route path="tasks/:taskId/submissions/:studentId" element={<SubmissionDetailPage />} />
        <Route path="students/:studentId" element={<StudentDetailPage />} />
        <Route path="roster" element={<RosterPage />} />
        <Route path="models" element={<ModelsPage />} />
        <Route path="sharing" element={<SharingManagePage />} />
        <Route path="backups" element={<BackupManagePage />} />
      </Route>

      {/* Super admin routes */}
      <Route
        path="/super-admin"
        element={
          <RequireAuth role="super_admin">
            <SuperAdminLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="admins" replace />} />
        <Route path="admins" element={<AdminManagePage />} />
      </Route>

      {/* Root redirect */}
      <Route path="/" element={<RootRedirect />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
