export interface Task {
  id: number;
  title: string;
  description: string;
  grading_criteria: string;
  status: "draft" | "published";
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
}

export interface TaskUpdateRequest {
  title?: string;
  description?: string;
  grading_criteria?: string;
  status?: "published";
}

export interface TaskSubmissionItem {
  student_id: string;
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
