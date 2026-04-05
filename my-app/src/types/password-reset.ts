export interface PasswordResetRequestItem {
  id: string;
  user_id: string;
  username: string;
  display_name: string | null;
  created_at: string;
}

export interface PasswordResetListResponse {
  items: PasswordResetRequestItem[];
}

export interface PasswordResetCountResponse {
  count: number;
}

export interface PasswordResetApproveResponse {
  approved_count: number;
}
