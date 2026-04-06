import { api } from "./client";
import type { ModelConfig, ModelConfigListResponse, ModelConfigCreateRequest, ModelConfigUpdateRequest, ModelDeriveRequest, ModelActivateResponse } from "@/types/model";

export const modelsApi = {
  list: () => api.get<ModelConfigListResponse>("/admin/models"),
  create: (data: ModelConfigCreateRequest) => api.post<ModelConfig>("/admin/models", data),
  update: (modelId: string, data: ModelConfigUpdateRequest) => api.patch<ModelConfig>(`/admin/models/${modelId}`, data),
  derive: (data: ModelDeriveRequest) => api.post<ModelConfig>("/admin/models/derive", data),
  activate: (modelId: string) => api.put<ModelActivateResponse>(`/admin/models/${modelId}/activate`),
  delete: (modelId: string) => api.delete(`/admin/models/${modelId}`),
};
