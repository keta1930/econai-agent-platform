export interface Task {
  id: number;
  title: string;
  description: string;
  grading_criteria: string;
  created_at: string;
}

export interface TaskListResponse {
  items: Task[];
}

export interface TaskCreateRequest {
  title: string;
  description: string;
  grading_criteria: string;
}

export interface TaskSubmissionItem {
  student_id: string;
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
