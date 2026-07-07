export const STATUS_INFO: Record<string, { label: string; color: string }> = {
  issue: { label: "Offline (Down)", color: "var(--status-issue)" },
  warning: { label: "Degraded", color: "var(--status-warning)" },
  resolving: { label: "Diagnosing", color: "var(--status-resolving)" },
  resolved: { label: "Resolved", color: "var(--status-online)" },
  online: { label: "Connected", color: "var(--text-primary)" },
  offline: { label: "Not connected", color: "var(--text-muted)" },
};
