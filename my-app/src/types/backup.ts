export interface BackupInfo {
  id: string;
  display_name: string;
  size: number;
  created_at: string;
}

export interface BackupListResponse {
  items: BackupInfo[];
}

export interface BackupDownloadResponse {
  download_url: string;
  filename: string;
}
