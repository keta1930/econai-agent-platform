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
  JoinClassRequest,
  JoinClassResponse,
  SwitchClassRequest,
  CaptchaResponse,
  ChangePasswordRequest,
  ChangePasswordResponse,
  UpdateProfileRequest,
  UpdateProfileResponse,
  MyClassesResponse,
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
  getCaptcha: () => api.get<CaptchaResponse>("/auth/captcha"),
  joinClass: (data: JoinClassRequest) =>
    api.post<JoinClassResponse>("/student/join-class", data),
  switchClass: (data: SwitchClassRequest) =>
    api.post<LoginResponse>("/student/switch-class", data),
  changePassword: (data: ChangePasswordRequest) =>
    api.post<ChangePasswordResponse>("/student/change-password", data),
  updateProfile: (data: UpdateProfileRequest) =>
    api.put<UpdateProfileResponse>("/student/profile", data),
  getMyClasses: () => api.get<MyClassesResponse>("/student/my-classes"),
};
