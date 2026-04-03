export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  role: string;
  class_id: number | null;
  class_name: string | null;
}

export interface ClassOption {
  class_id: number;
  class_name: string;
  admin_name: string;
}

export interface ClassSelectionResponse {
  requires_class_selection: true;
  classes: ClassOption[];
}

export interface SelectClassRequest {
  username: string;
  password: string;
  class_id: number;
}

export interface RegisterRequest {
  class_name: string;
  admin_name: string;
  student_id: string;
  password: string;
}

export interface RegisterResponse {
  id: number;
  role: string;
}

export type LoginResult = LoginResponse | ClassSelectionResponse;

export function isClassSelection(result: LoginResult): result is ClassSelectionResponse {
  return "requires_class_selection" in result;
}
