import { api } from "./client";

export interface AdminInfo {
  id: string;
  username: string;
  role: string;
  is_active: boolean;
  class_count: number;
  category: string | null;
  created_at: string;
}

export interface AdminListResponse {
  items: AdminInfo[];
}

export const superAdminApi = {
  listAdmins: () => api.get<AdminListResponse>("/super-admin/admins"),
  toggleActive: (adminId: string) =>
    api.put<AdminInfo>(`/super-admin/admins/${adminId}/toggle-active`),
  deleteAdmin: (adminId: string) =>
    api.delete(`/super-admin/admins/${adminId}`),
  resetPassword: (adminId: string, newPassword: string) =>
    api.put(`/super-admin/admins/${adminId}/reset-password`, {
      new_password: newPassword,
    }),
};
