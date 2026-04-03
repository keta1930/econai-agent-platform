import { api } from "./client";
import type {
  BackupInfo,
  BackupListResponse,
  BackupDownloadResponse,
} from "@/types/backup";

export const backupsApi = {
  list: () => api.get<BackupListResponse>("/admin/backups"),
  create: () => api.post<BackupInfo>("/admin/backups"),
  getDownloadUrl: (filename: string) =>
    api.get<BackupDownloadResponse>(`/admin/backups/${filename}`),
  delete: (filename: string) => api.delete(`/admin/backups/${filename}`),
};
