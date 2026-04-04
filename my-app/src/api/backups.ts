import { api } from "./client";
import type {
  BackupInfo,
  BackupListResponse,
  BackupDownloadResponse,
} from "@/types/backup";

export const backupsApi = {
  list: () => api.get<BackupListResponse>("/admin/backups"),

  create: (displayName?: string) =>
    api.post<BackupInfo>(
      "/admin/backups",
      displayName ? { display_name: displayName } : undefined,
    ),

  getDownloadUrl: (id: string) =>
    api.get<BackupDownloadResponse>(`/admin/backups/${id}/download`),

  rename: (id: string, displayName: string) =>
    api.patch<BackupInfo>(`/admin/backups/${id}`, {
      display_name: displayName,
    }),

  delete: (id: string) => api.delete(`/admin/backups/${id}`),
};
