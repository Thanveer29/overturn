const LABELS: Record<string, { label: string; variant: string }> = {
  pending_appeal: { label: "Pending", variant: "pending" },
  resolved_approved: { label: "Approved", variant: "approved" },
  resolved_rejected: { label: "Rejected", variant: "rejected" },
};

export function StatusBadge({ status }: { status: string }) {
  const info = LABELS[status] ?? { label: status, variant: "pending" };
  return <span className={`badge badge--${info.variant}`}>{info.label}</span>;
}
