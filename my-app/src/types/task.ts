export interface LearningResource {
  url: string;
  title: string;
  content: string;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  grading_criteria: string;
  learning_resources: LearningResource[] | null;
  status: "draft" | "published";
  class_id: string;
  created_by: string;
  created_at: string;
  updated_at: string | null;
  class_name: string;
  created_by_name: string;
}

export interface TaskListResponse {
  items: Task[];
}

export interface TaskDraftRequest {
  title: string;
  description?: string;
  grading_criteria?: string;
  learning_resources?: LearningResource[] | null;
  class_id: string;
}

export interface TaskUpdateRequest {
  title?: string;
  description?: string;
  grading_criteria?: string;
  learning_resources?: LearningResource[] | null;
  status?: "published";
}

export interface TaskSubmissionItem {
  student_id: string;
  username: string;
  version: number;
  submission_count: number;
  status: string;
  score: number | null;
  submitted_at: string;
}

export interface TaskStatsResponse {
  task_id: string;
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
  learning_resources?: LearningResource[] | null;
  class_ids: string[];
  status: "published";
}

export interface BatchPublishResponse {
  created: { id: string; class_id: string; class_name: string }[];
}
