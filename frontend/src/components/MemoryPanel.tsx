import type { RecalledMemory } from "../types";

/** Pulls "HC-###" case references out of the strategy text so the panel can
 * show a citation trail, not just a dump of everything recall() returned. */
function extractCitedCaseIds(text: string): string[] {
  const matches = text.match(/HC-\d{3}/g) ?? [];
  return Array.from(new Set(matches));
}

/** recall() intentionally returns broad, unfiltered matches (see
 * docs/architecture/agent-orchestrator.md's "known follow-ups") -- narrow to
 * what the recommendation actually cited, falling back to the first few
 * results when nothing was explicitly cited (e.g. the without-memory panel
 * has none, or reflect() paraphrased without naming a case id). */
function relevantMemories(memories: RecalledMemory[], citedIds: string[]): RecalledMemory[] {
  if (citedIds.length === 0) return memories.slice(0, 8);
  const cited = memories.filter((m) => citedIds.some((id) => m.text.includes(id)));
  return cited.length > 0 ? cited : memories.slice(0, 8);
}

export function MemoryPanel({
  strategyText,
  memories,
}: {
  strategyText: string;
  memories: RecalledMemory[];
}) {
  const citedIds = extractCitedCaseIds(strategyText);
  const shown = relevantMemories(memories, citedIds);

  return (
    <div>
      {citedIds.length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <span className="muted" style={{ fontSize: "0.82rem", marginRight: 8 }}>
            Historical cases cited:
          </span>
          {citedIds.map((id) => (
            <span key={id} className="memory-chip">
              {id}
            </span>
          ))}
        </div>
      )}
      <ul className="memory-list">
        {shown.map((m, i) => (
          <li key={i} className="memory-item">
            <span className="memory-item__type">{m.type}</span>
            <div>{m.text}</div>
          </li>
        ))}
      </ul>
      <p className="muted" style={{ fontSize: "0.78rem", marginTop: 8 }}>
        Showing {shown.length} of {memories.length} memories recalled from Hindsight for this
        claim, filtered to those referenced in the recommendation above.
      </p>
    </div>
  );
}
