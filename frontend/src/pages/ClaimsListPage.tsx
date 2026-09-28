import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import type { ClaimSummary } from "../types";

export default function ClaimsListPage() {
  const [claims, setClaims] = useState<ClaimSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api
      .listClaims()
      .then(setClaims)
      .catch((e) => setError(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e)));
  }, []);

  return (
    <>
      <h1 className="page-title">Denial Workbench</h1>
      <p className="page-subtitle">
        Pending appeals for Riverside Medical Group. Select a claim to analyze it with and without
        institutional memory.
      </p>

      {error && <div className="error-banner">Could not load claims: {error}</div>}

      <div className="card">
        {claims === null && !error && <p className="spinner-text">Loading claims…</p>}
        {claims && (
          <table className="claims-table">
            <thead>
              <tr>
                <th>Claim</th>
                <th>Insurer</th>
                <th>Procedure</th>
                <th>Denial reason</th>
                <th>Patient</th>
                <th>Denied</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {claims.map((c) => (
                <tr
                  key={c.claim_id}
                  className="clickable"
                  onClick={() => navigate(`/claims/${c.claim_id}`)}
                >
                  <td>
                    <strong>{c.claim_id}</strong>
                  </td>
                  <td>{c.insurer_name}</td>
                  <td>{c.procedure_name}</td>
                  <td>{c.denial_reason_name}</td>
                  <td>{c.patient_name}</td>
                  <td>{c.denial_date}</td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
