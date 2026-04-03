import { api } from "./client";
import type {
  LoginRequest,
  LoginResult,
  RegisterRequest,
  RegisterResponse,
  SelectClassRequest,
  LoginResponse,
} from "@/types/auth";

export const authApi = {
  login: (data: LoginRequest) => api.post<LoginResult>("/auth/login", data),
  register: (data: RegisterRequest) =>
    api.post<RegisterResponse>("/auth/register", data),
  selectClass: (data: SelectClassRequest) =>
    api.post<LoginResponse>("/auth/login/select-class", data),
};
