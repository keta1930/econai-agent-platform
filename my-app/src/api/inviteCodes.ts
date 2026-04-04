import { api } from "./client";

export interface InviteCodeInfo {
  id: string;
  category: string;
  registered_count: number;
  created_at: string;
}

export interface InviteCodeCreateResponse extends InviteCodeInfo {
  code: string;
}

export interface InviteCodeListResponse {
  items: InviteCodeInfo[];
}

export const inviteCodeApi = {
  list: () => api.get<InviteCodeListResponse>("/super-admin/invite-codes"),
  create: (category: string) =>
    api.post<InviteCodeCreateResponse>("/super-admin/invite-codes", { category }),
  delete: (id: string) =>
    api.delete<undefined>(`/super-admin/invite-codes/${id}`),
  regenerate: (id: string) =>
    api.post<InviteCodeCreateResponse>(`/super-admin/invite-codes/${id}/regenerate`),
};
