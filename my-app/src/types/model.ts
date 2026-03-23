export interface ModelConfig {
  id: number;
  name: string;
  base_url: string;
  adapter_type: string;
  is_active: boolean;
  created_at: string;
}

export interface ModelConfigListResponse {
  items: ModelConfig[];
}

export interface ModelConfigCreateRequest {
  name: string;
  api_key: string;
  base_url: string;
  adapter_type: "openai" | "anthropic";
}

export interface ModelActivateResponse {
  message: string;
  active_model: string;
}
