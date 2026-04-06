import { api, coalesceRefresh, clearAuthAndRedirect } from "./client";
import type { BackupInfo, BackupListResponse } from "@/types/backup";

async function fetchWithAuth(url: string): Promise<Response> {
  const token = localStorage.getItem("token");
  const response = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (response.status === 401) {
    let newToken: string;
    try {
      newToken = await coalesceRefresh();
    } catch {
      clearAuthAndRedirect();
      throw new Error("认证已过期");
    }
    return fetch(url, {
      headers: { Authorization: `Bearer ${newToken}` },
    });
  }

  return response;
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export const backupsApi = {
  list: () => api.get<BackupListResponse>("/admin/backups"),

  create: (displayName?: string) =>
    api.post<BackupInfo>(
      "/admin/backups",
      displayName ? { display_name: displayName } : undefined,
    ),

  download: async (id: string, filename?: string) => {
    const response = await fetchWithAuth(`/api/admin/backups/${id}/download`);
    if (!response.ok) throw new Error("下载失败");
    const blob = await response.blob();
    triggerDownload(blob, filename ?? "backup.json");
  },

  rename: (id: string, displayName: string) =>
    api.patch<BackupInfo>(`/admin/backups/${id}`, {
      display_name: displayName,
    }),

  delete: (id: string) => api.delete(`/admin/backups/${id}`),
};
