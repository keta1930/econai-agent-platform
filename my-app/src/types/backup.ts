export interface BackupInfo {
  filename: string;
  size: number;
  created_at: string;
}

export interface BackupListResponse {
  items: BackupInfo[];
}

export interface BackupDownloadResponse {
  download_url: string;
}
