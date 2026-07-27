export interface MissionsResponse {
  missions: string[];
}

export interface QueryRequest {
  question: string;
  mission_filter: string | null;
}

export interface SourceItem {
  record_id: number;
  mission: string;
  chunk_index: number;
}

export interface QueryResponse {
  answer: string;
  sources: SourceItem[];
}
