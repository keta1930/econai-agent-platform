export interface BackupInfo {
  id: string;
  display_name: string;
  size: number;
  created_at: string;
}

export interface BackupListResponse {
  items: BackupInfo[];
}
