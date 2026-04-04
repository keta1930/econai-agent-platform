export interface ExpectedRosterItem {
  student_id: string;
  matched: boolean;
}

export interface ActualRosterItem {
  user_id: string;
  student_id: string;
  display_name: string | null;
  college: string | null;
  joined_at: string;
}

export interface RosterListResponse {
  expected: ExpectedRosterItem[];
  actual: ActualRosterItem[];
}

export interface RosterBatchResponse {
  added: number;
  duplicates: number;
}
