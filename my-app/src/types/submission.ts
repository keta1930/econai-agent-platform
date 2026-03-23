export interface SubmissionCreateResponse {
  id: number;
  task_id: number;
  student_id: string;
  status: string;
  submitted_at: string;
}

export interface SubmissionDetail {
  id: number;
  task_id: number;
  task_title: string;
  status: string;
  score: number | null;
  suggestion: string | null;
  submitted_at: string;
  graded_at: string | null;
}

export interface SubmissionListResponse {
  items: SubmissionDetail[];
}
