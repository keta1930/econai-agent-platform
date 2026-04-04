import { api } from "./client";

export interface AdminInfo {
  id: string;
  username: string;
  role: string;
  class_count: number;
  created_at: string;
}

export interface AdminListResponse {
  items: AdminInfo[];
}

export interface AdminCreateRequest {
  username: string;
  password: string;
}

export const superAdminApi = {
  listAdmins: () => api.get<AdminListResponse>("/super-admin/admins"),
  createAdmin: (data: AdminCreateRequest) =>
    api.post<AdminInfo>("/super-admin/admins", data),
};
