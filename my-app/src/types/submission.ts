export interface SubmissionCreateResponse {
  id: string;
  task_id: string;
  student_id: string;
  version: number;
  content_type: string;
  status: string;
  submitted_at: string;
  task_title: string;
}

export interface SubmissionDetail {
  id: string;
  task_id: string;
  task_title: string;
  version: number;
  content_type: string;
  status: string;
  score: number | null;
  suggestion: string | null;
  submitted_at: string;
  graded_at: string | null;
}

export interface SubmissionListResponse {
  items: SubmissionDetail[];
  student_name?: string;
}

export interface SubmissionContentResponse {
  submission_id: string;
  filename: string;
  content: string;
  content_type: string;
  file_extension: string;
}
