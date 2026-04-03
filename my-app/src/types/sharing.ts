export type TopicStatus = "voting" | "confirmed" | "completed";

export interface TopicListItem {
  id: number;
  title: string;
  status: TopicStatus;
  presenters: string | null;
  session_number: number | null;
  shared_at: string | null;
  has_materials: boolean;
  vote_count: number;
  current_user_voted: boolean;
  is_student_submitted: boolean;
  submitted_by_name: string | null;
}

export interface TopicListResponse {
  items: TopicListItem[];
  total_votes: number;
}

export interface TopicMaterialsResponse {
  topic_id: number;
  title: string;
  materials_content: string;
}

export interface VoteResponse {
  vote_count: number;
}

export interface AdminTopicListItem extends TopicListItem {
  materials_content: string | null;
}

export interface AdminTopicListResponse {
  items: AdminTopicListItem[];
}

export interface TopicCreateRequest {
  title: string;
  class_id: number;
  status?: TopicStatus;
  presenters?: string | null;
  session_number?: number | null;
  shared_at?: string | null;
  materials_content?: string | null;
}

export interface TopicUpdateRequest {
  title?: string;
  status?: TopicStatus;
  presenters?: string | null;
  session_number?: number | null;
  shared_at?: string | null;
  materials_content?: string | null;
}

export interface TopicSuggestRequest {
  title: string;
}
