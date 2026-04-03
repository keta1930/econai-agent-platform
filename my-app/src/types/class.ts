export interface ClassInfo {
  id: number;
  name: string;
  student_count: number;
  created_at: string;
}

export interface ClassListResponse {
  items: ClassInfo[];
}

export interface ClassCreateRequest {
  name: string;
}
