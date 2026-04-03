export interface Task {
  id: number;
  title: string;
  description: string;
  grading_criteria: string;
  status: "draft" | "published";
  class_id: number;
  created_by: number;
  created_at: string;
  updated_at: string | null;
}

export interface TaskListResponse {
  items: Task[];
}

export interface TaskDraftRequest {
  title: string;
  description?: string;
  grading_criteria?: string;
  class_id: number;
}

export interface TaskUpdateRequest {
  title?: string;
  description?: string;
  grading_criteria?: string;
  status?: "published";
}

export interface TaskSubmissionItem {
  student_id: number;
  username: string;
  version: number;
  submission_count: number;
  status: string;
  score: number | null;
  submitted_at: string;
}

export interface TaskStatsResponse {
  task_id: number;
  total_students: number;
  submitted_count: number;
  submission_rate: number;
  submissions: TaskSubmissionItem[];
  not_submitted: string[];
}

export interface GenerateCriteriaRequest {
  title: string;
  description: string;
}

export interface GenerateCriteriaResponse {
  criteria: string;
}

export interface BatchPublishRequest {
  title: string;
  description: string;
  grading_criteria: string;
  class_ids: number[];
  status: "published";
}

export interface BatchPublishResponse {
  created: { id: number; class_id: number; class_name: string }[];
}
