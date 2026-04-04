import { api } from "./client";
import type { ModelConfig, ModelConfigListResponse, ModelConfigCreateRequest, ModelActivateResponse } from "@/types/model";

export const modelsApi = {
  list: () => api.get<ModelConfigListResponse>("/admin/models"),
  create: (data: ModelConfigCreateRequest) => api.post<ModelConfig>("/admin/models", data),
  activate: (modelId: string) => api.put<ModelActivateResponse>(`/admin/models/${modelId}/activate`),
};
