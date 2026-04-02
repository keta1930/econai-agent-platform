export interface SubmissionCreateResponse {
  id: number;
  task_id: number;
  student_id: string;
  version: number;
  status: string;
  submitted_at: string;
}

export interface SubmissionDetail {
  id: number;
  task_id: number;
  task_title: string;
  version: number;
  status: string;
  score: number | null;
  suggestion: string | null;
  submitted_at: string;
  graded_at: string | null;
}

export interface SubmissionListResponse {
  items: SubmissionDetail[];
}

export interface SubmissionContentResponse {
  submission_id: number;
  filename: string;
  content: string;
}
