import { TerminalSquare, ChevronDown, ChevronUp } from "lucide-react";
import { Incident } from "../lib/types";
import { useState } from "react";
import { getDiagnosisSummaryMarkdown } from "../lib/diagnosisSummary";
import { renderMarkdownBlocks } from "../lib/renderMarkdown";
import { STATUS_INFO } from "../lib/statusInfo";

function formatAge(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const m = Math.floor(ms / 60_000);
  if (m < 1) return "Just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export const IncidentCard = ({
  incident,
  onReview,
}: {
  incident: Incident;
  onReview: () => void;
  isLast?: boolean;
}) => {
  const [expanded, setExpanded] = useState(
    incident.status === "issue" || incident.status === "resolving",
  );

  const { label: statusLabel, color: statusColor } =
    STATUS_INFO[incident.status] ?? { label: incident.status, color: "var(--text-secondary)" };

  const confidencePct =
    incident.confidence > 0 ? `${Math.round(incident.confidence * 100)}%` : "—";

  const detectedLabel = incident.detectedAt ? formatAge(incident.detectedAt) : "—";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        borderBottom: "1px solid var(--borderColor)",
      }}
      className="ts-row-hover"
    >
      {/* Table row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            "minmax(250px, 2fr) minmax(150px, 1fr) minmax(150px, 1fr) minmax(150px, 1fr) 40px",
          alignItems: "center",
          padding: "1.25rem 1rem",
          cursor: "pointer",
          transition: "background-color 0.15s",
        }}
        onMouseEnter={(e) =>
          (e.currentTarget.style.backgroundColor = "var(--bg-surface)")
        }
        onMouseLeave={(e) =>
          (e.currentTarget.style.backgroundColor = "transparent")
        }
        onClick={() => setExpanded(!expanded)}
      >
        {/* SERVICE */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.125rem" }}>
          <span style={{ fontWeight: 600, fontSize: "0.875rem", color: "var(--text-primary)" }}>
            {incident.service}
          </span>
          <span style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
            {incident.serviceType}
          </span>
          {incident.status !== "online" && incident.status !== "resolved" && (
            <div style={{ marginTop: "0.375rem" }}>
              <span
                style={{
                  fontSize: "0.625rem",
                  backgroundColor: "rgba(239, 68, 68, 0.2)",
                  color: "#FCA5A5",
                  padding: "0.125rem 0.375rem",
                  borderRadius: "4px",
                  fontWeight: 600,
                }}
              >
                Action Required
              </span>
            </div>
          )}
        </div>

        {/* STATUS */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.8125rem" }}>
          <span className={`status-dot ${incident.status}`}></span>
          <span style={{ color: statusColor }}>{statusLabel}</span>
        </div>

        {/* CONFIDENCE */}
        <div
          style={{
            fontSize: "0.8125rem",
            color: incident.confidence > 0 ? "var(--text-primary)" : "var(--text-muted)",
            fontWeight: incident.confidence > 0 ? 500 : 400,
          }}
        >
          {confidencePct}
        </div>

        {/* DETECTED */}
        <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
          {detectedLabel}
        </div>

        {/* EXPAND */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--text-muted)",
          }}
        >
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>

      {/* Expanded agent output */}
      {expanded &&
        (incident.status === "issue" || incident.status === "resolving") && (
          <div
            style={{
              padding: "0 1rem 1.5rem 1rem",
              display: "flex",
              flexDirection: "column",
              gap: "1rem",
              borderTop: "1px solid rgba(255,255,255,0.05)",
              backgroundColor: "rgba(255,255,255,0.01)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginTop: "1rem",
              }}
            >
              <h4
                style={{
                  margin: 0,
                  fontSize: "0.875rem",
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                <TerminalSquare size={16} color="var(--accent-text)" /> AI
                Diagnostic Stream
              </h4>
            </div>

            <div
              style={{
                backgroundColor: "#000000",
                borderRadius: "var(--radius-md)",
                padding: "1rem",
                fontFamily:
                  '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                fontSize: "0.8125rem",
                color: "#E5E7EB",
                border: "1px solid #333",
              }}
            >
              <div className="flex-col gap-1.5">
                {incident.logs.map((log: string, i: number) => (
                  <div
                    key={i}
                    style={{ display: "flex", gap: "0.75rem", lineHeight: 1.6 }}
                  >
                    <span style={{ color: "#60A5FA", userSelect: "none" }}>$</span>
                    <span style={{ color: "#D4D4D8" }}>{log}</span>
                  </div>
                ))}
              </div>
            </div>

            {incident.proposedFix && (
              <div
                style={{
                  border: "1px solid var(--borderColor)",
                  borderRadius: "var(--radius-md)",
                  padding: "1.25rem",
                  backgroundColor: "var(--bg-surface)",
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "1.5rem",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div style={{ flex: 1, minWidth: "300px" }}>
                  <div
                    style={{
                      fontSize: "0.875rem",
                      fontWeight: 600,
                      color: "var(--text-primary)",
                      marginBottom: "0.375rem",
                    }}
                  >
                    Auto-Healer Plan Ready
                  </div>
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.5rem",
                      maxHeight: "220px",
                      overflow: "hidden",
                    }}
                  >
                    {renderMarkdownBlocks(getDiagnosisSummaryMarkdown(incident), 5)}
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    className="btn btn-primary"
                    onClick={(e) => {
                      e.stopPropagation();
                      onReview();
                    }}
                  >
                    Review Suggestions
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={(e) => {
                      e.stopPropagation();
                      setExpanded(false);
                    }}
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
    </div>
  );
};

export default IncidentCard;
