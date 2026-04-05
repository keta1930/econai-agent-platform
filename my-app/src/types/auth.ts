export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  role: string;
  class_id: string | null;
  class_name: string | null;
  admin_name: string | null;
}

export interface ClassOption {
  class_id: string;
  class_name: string;
  admin_name: string;
}

export interface ClassSelectionResponse {
  requires_class_selection: true;
  temp_access_token: string;
  temp_refresh_token: string;
  classes: ClassOption[];
}

export interface JoinClassRequiresResponse {
  requires_join_class: true;
  temp_access_token: string;
  temp_refresh_token: string;
}

export interface SelectClassRequest {
  class_id: string;
}

export interface RegisterRequest {
  student_id: string;
  password: string;
}

export interface RegisterResponse {
  id: string;
  role: string;
}

export interface TeacherRegisterRequest {
  invite_code: string;
  username: string;
  password: string;
}

export interface TeacherRegisterResponse {
  id: string;
  role: string;
}

export interface RefreshResponse {
  access_token: string;
}

export interface JoinClassRequest {
  join_token: string;
}

export interface JoinClassResponse {
  class_id: string;
  class_name: string;
  admin_name: string;
  access_token: string;
  refresh_token: string;
}

export interface SwitchClassRequest {
  class_id: string;
}

export interface CaptchaResponse {
  captcha_id: string;
  question: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ChangePasswordResponse {
  password_change_count: number;
}

export interface UpdateProfileRequest {
  display_name: string;
}

export interface UpdateProfileResponse {
  display_name: string;
}

export interface MyClassItem {
  class_id: string;
  class_name: string;
  admin_name: string;
}

export interface MyClassesResponse {
  classes: MyClassItem[];
}

export type LoginResult =
  | LoginResponse
  | ClassSelectionResponse
  | JoinClassRequiresResponse;

export function isClassSelection(
  result: LoginResult,
): result is ClassSelectionResponse {
  return "requires_class_selection" in result;
}

export function isJoinClassRequired(
  result: LoginResult,
): result is JoinClassRequiresResponse {
  return "requires_join_class" in result;
}
