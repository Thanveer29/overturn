export interface ClaimSummary {
  claim_id: string;
  insurer_name: string;
  procedure_name: string;
  denial_reason_name: string;
  patient_name: string;
  denial_date: string;
  status: string;
}

export interface ClaimDetail extends ClaimSummary {
  provider_name: string;
  evidence_available: string[];
  demo_scenario: string;
}

export interface RecalledMemory {
  type: string;
  text: string;
}

export type AnalysisMode = "with_memory" | "without_memory";

export interface AnalyzeResponse {
  mode: AnalysisMode;
  strategy_text: string;
  recalled_memories: RecalledMemory[];
}

export interface DraftResponse {
  draft: string;
}

export interface OutcomeResponse {
  status: string;
}
