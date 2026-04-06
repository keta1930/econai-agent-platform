export interface ModelConfig {
  id: string;
  name: string;
  base_url: string;
  adapter_type: string;
  supports_vision: boolean;
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
  supports_vision?: boolean;
}

export interface ModelConfigUpdateRequest {
  name?: string;
  api_key?: string;
  base_url?: string;
  adapter_type?: "openai" | "anthropic";
  supports_vision?: boolean;
}

export interface ModelDeriveRequest {
  source_model_id: string;
  name: string;
  supports_vision?: boolean;
}

export interface ModelActivateResponse {
  message: string;
  active_model: string;
}
