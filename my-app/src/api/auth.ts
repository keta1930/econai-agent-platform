import { api } from "./client";
import type {
  LoginRequest,
  LoginResult,
  RegisterRequest,
  RegisterResponse,
  SelectClassRequest,
  LoginResponse,
  TeacherRegisterRequest,
  TeacherRegisterResponse,
  RefreshResponse,
} from "@/types/auth";

export const authApi = {
  login: (data: LoginRequest) => api.post<LoginResult>("/auth/login", data),
  register: (data: RegisterRequest) =>
    api.post<RegisterResponse>("/auth/register", data),
  selectClass: (data: SelectClassRequest) =>
    api.post<LoginResponse>("/auth/login/select-class", data),
  registerTeacher: (data: TeacherRegisterRequest) =>
    api.post<TeacherRegisterResponse>("/auth/register-teacher", data),
  refresh: (refreshToken: string) =>
    api.post<RefreshResponse>("/auth/refresh", { refresh_token: refreshToken }),
  logout: (refreshToken: string) =>
    api.post<undefined>("/auth/logout", { refresh_token: refreshToken }),
};
