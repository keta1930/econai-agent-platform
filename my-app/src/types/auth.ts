export interface LoginRequest {
  id: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
}

export interface RegisterRequest {
  student_id: string;
  password: string;
}

export interface RegisterResponse {
  id: string;
  role: string;
}
