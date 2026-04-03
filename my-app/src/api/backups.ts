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

  getDownloadUrl: (id: number) =>
    api.get<BackupDownloadResponse>(`/admin/backups/${id}/download`),

  rename: (id: number, displayName: string) =>
    api.patch<BackupInfo>(`/admin/backups/${id}`, {
      display_name: displayName,
    }),

  delete: (id: number) => api.delete(`/admin/backups/${id}`),
};
