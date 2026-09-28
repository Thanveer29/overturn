import type {
  AnalysisMode,
  AnalyzeResponse,
  ClaimDetail,
  ClaimSummary,
  DraftResponse,
  OutcomeResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON -- keep statusText
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listClaims: () => request<ClaimSummary[]>("/api/claims"),

  getClaim: (claimId: string) => request<ClaimDetail>(`/api/claims/${claimId}`),

  analyze: (claimId: string, mode: AnalysisMode) =>
    request<AnalyzeResponse>(`/api/claims/${claimId}/analyze`, {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),

  draft: (claimId: string, strategyText: string) =>
    request<DraftResponse>(`/api/claims/${claimId}/draft`, {
      method: "POST",
      body: JSON.stringify({ strategy_text: strategyText }),
    }),

  recordOutcome: (claimId: string, outcome: "approved" | "rejected", notes: string) =>
    request<OutcomeResponse>(`/api/claims/${claimId}/outcome`, {
      method: "POST",
      body: JSON.stringify({ outcome, notes }),
    }),
};
