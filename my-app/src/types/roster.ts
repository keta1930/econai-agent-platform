export interface RosterItem {
  student_id: string;
  registered: boolean;
}

export interface RosterListResponse {
  items: RosterItem[];
  total: number;
}

export interface RosterBatchResponse {
  added: number;
  duplicates: number;
}
