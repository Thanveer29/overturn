import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { Markdown } from "../components/Markdown";
import { MemoryPanel } from "../components/MemoryPanel";
import { StatusBadge } from "../components/StatusBadge";
import type { AnalyzeResponse, ClaimDetail } from "../types";

function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return `${e.status}: ${e.message}`;
  if (e instanceof Error) return e.message;
  return String(e);
}

export default function ClaimDetailPage() {
  const { claimId } = useParams<{ claimId: string }>();

  const [claim, setClaim] = useState<ClaimDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [withoutMemory, setWithoutMemory] = useState<AnalyzeResponse | null>(null);
  const [withMemory, setWithMemory] = useState<AnalyzeResponse | null>(null);

  const [drafting, setDrafting] = useState(false);
  const [draft, setDraft] = useState<string | null>(null);
  const [draftError, setDraftError] = useState<string | null>(null);

  const [outcome, setOutcome] = useState<"approved" | "rejected">("approved");
  const [notes, setNotes] = useState("");
  const [recording, setRecording] = useState(false);
  const [outcomeMessage, setOutcomeMessage] = useState<string | null>(null);
  const [outcomeError, setOutcomeError] = useState<string | null>(null);

  useEffect(() => {
    if (!claimId) return;
    api
      .getClaim(claimId)
      .then(setClaim)
      .catch((e) => setLoadError(errorMessage(e)));
  }, [claimId]);

  async function runAnalysis() {
    if (!claimId) return;
    setAnalyzing(true);
    setAnalyzeError(null);
    setWithoutMemory(null);
    setWithMemory(null);
    setDraft(null);
    try {
      const [without, withMem] = await Promise.all([
        api.analyze(claimId, "without_memory"),
        api.analyze(claimId, "with_memory"),
      ]);
      setWithoutMemory(without);
      setWithMemory(withMem);
    } catch (e) {
      setAnalyzeError(errorMessage(e));
    } finally {
      setAnalyzing(false);
    }
  }

  async function generateDraft() {
    if (!claimId || !withMemory) return;
    setDrafting(true);
    setDraftError(null);
    try {
      const res = await api.draft(claimId, withMemory.strategy_text);
      setDraft(res.draft);
    } catch (e) {
      setDraftError(errorMessage(e));
    } finally {
      setDrafting(false);
    }
  }

  async function submitOutcome() {
    if (!claimId) return;
    setRecording(true);
    setOutcomeError(null);
    setOutcomeMessage(null);
    try {
      await api.recordOutcome(claimId, outcome, notes);
      setOutcomeMessage(`Outcome recorded and retained into institutional memory as ${outcome}.`);
      setClaim((prev) => (prev ? { ...prev, status: `resolved_${outcome}` } : prev));
    } catch (e) {
      setOutcomeError(errorMessage(e));
    } finally {
      setRecording(false);
    }
  }

  if (loadError) {
    return <div className="error-banner">Could not load claim: {loadError}</div>;
  }
  if (!claim) {
    return <p className="spinner-text">Loading claim…</p>;
  }

  return (
    <>
      <Link to="/" className="back-link">
        &larr; Back to Denial Workbench
      </Link>
      <h1 className="page-title">{claim.claim_id}</h1>
      <p className="page-subtitle">{claim.demo_scenario}</p>

      <div className="card">
        <h2>Claim details</h2>
        <table className="claims-table">
          <tbody>
            <tr>
              <td className="muted">Insurer</td>
              <td>{claim.insurer_name}</td>
            </tr>
            <tr>
              <td className="muted">Procedure</td>
              <td>{claim.procedure_name}</td>
            </tr>
            <tr>
              <td className="muted">Denial reason</td>
              <td>{claim.denial_reason_name}</td>
            </tr>
            <tr>
              <td className="muted">Patient</td>
              <td>{claim.patient_name}</td>
            </tr>
            <tr>
              <td className="muted">Ordering provider</td>
              <td>{claim.provider_name}</td>
            </tr>
            <tr>
              <td className="muted">Denied on</td>
              <td>{claim.denial_date}</td>
            </tr>
            <tr>
              <td className="muted">Status</td>
              <td>
                <StatusBadge status={claim.status} />
              </td>
            </tr>
          </tbody>
        </table>
        <h2 style={{ marginTop: 18 }}>Evidence currently available</h2>
        {claim.evidence_available.length === 0 ? (
          <p className="muted">None on file.</p>
        ) : (
          <ul className="evidence-list">
            {claim.evidence_available.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h2>Appeal strategy: without memory vs. with Hindsight</h2>
        <p className="page-subtitle" style={{ marginBottom: 14 }}>
          Runs this claim through the agent twice: once with no institutional memory, once with
          full access to Riverside's appeal history via Hindsight.
        </p>
        <button className="btn btn--primary" onClick={runAnalysis} disabled={analyzing}>
          {analyzing ? "Analyzing…" : "Analyze this claim"}
        </button>

        {analyzeError && (
          <div className="error-banner" style={{ marginTop: 14 }}>
            {analyzeError}
          </div>
        )}

        {(withoutMemory || withMemory || analyzing) && (
          <div className="compare-grid" style={{ marginTop: 18 }}>
            <div className="panel panel--without">
              <div className="panel__label">Without memory — generic</div>
              <div className="panel__body">
                {withoutMemory ? (
                  <Markdown text={withoutMemory.strategy_text} />
                ) : (
                  analyzing && "Thinking…"
                )}
              </div>
            </div>
            <div className="panel panel--with">
              <div className="panel__label">With Hindsight — institutional</div>
              <div className="panel__body">
                {withMemory ? <Markdown text={withMemory.strategy_text} /> : analyzing && "Thinking…"}
              </div>
            </div>
          </div>
        )}
      </div>

      {withMemory && (
        <div className="card">
          <h2>Why did Overturn recommend this?</h2>
          <MemoryPanel strategyText={withMemory.strategy_text} memories={withMemory.recalled_memories} />
        </div>
      )}

      {withMemory && (
        <div className="card">
          <h2>Appeal draft</h2>
          <button className="btn btn--secondary" onClick={generateDraft} disabled={drafting}>
            {drafting ? "Drafting…" : "Generate appeal draft"}
          </button>
          {draftError && (
            <div className="error-banner" style={{ marginTop: 14 }}>
              {draftError}
            </div>
          )}
          {draft && (
            <>
              <div className="draft-output" style={{ marginTop: 14 }}>
                <Markdown text={draft} />
              </div>
              <p className="muted" style={{ marginTop: 10, fontSize: "0.82rem" }}>
                This is a draft for human review only. Overturn never submits appeals
                automatically.
              </p>
            </>
          )}
        </div>
      )}

      <div className="card">
        <h2>Record outcome</h2>
        <p className="page-subtitle" style={{ marginBottom: 14 }}>
          Recording an outcome retains it into Hindsight, so future claims for this insurer and
          procedure benefit from what happened here.
        </p>
        <div className="form-row">
          <label>Outcome</label>
          <div className="radio-group">
            <label>
              <input
                type="radio"
                name="outcome"
                checked={outcome === "approved"}
                onChange={() => setOutcome("approved")}
              />
              Approved
            </label>
            <label>
              <input
                type="radio"
                name="outcome"
                checked={outcome === "rejected"}
                onChange={() => setOutcome("rejected")}
              />
              Rejected
            </label>
          </div>
        </div>
        <div className="form-row">
          <label>Notes</label>
          <textarea
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="What evidence was ultimately submitted, and why did the insurer decide as it did?"
          />
        </div>
        <button className="btn btn--primary" onClick={submitOutcome} disabled={recording}>
          {recording ? "Recording…" : "Record outcome"}
        </button>
        {outcomeError && (
          <div className="error-banner" style={{ marginTop: 14 }}>
            {outcomeError}
          </div>
        )}
        {outcomeMessage && (
          <div className="info-banner" style={{ marginTop: 14 }}>
            {outcomeMessage}
          </div>
        )}
      </div>
    </>
  );
}
