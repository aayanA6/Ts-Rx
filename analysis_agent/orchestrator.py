from __future__ import annotations

import logging

from pydantic import ValidationError

from analysis_agent import service_kb
from analysis_agent.config import get_settings
from analysis_agent.fallback import build_fallback_report
from analysis_agent.gemini_client import GeminiClientError
from analysis_agent.retriever import SelectiveCodeRetriever
from analysis_agent.schemas import AnalysisJobCreate, AnalysisReport, EvidenceItem
from analysis_agent.specialist import ServiceSpecialist, _extract_section_bullets

logger = logging.getLogger(__name__)


class Orchestrator:
    """The main agent watching over every service. It routes each incoming
    incident to a per-service ServiceSpecialist (deploying and caching one
    per service_name as incidents arrive), and records the outcome to that
    service's knowledge-base file for future incidents to draw on."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.retriever = SelectiveCodeRetriever()
        self._specialists: dict[str, ServiceSpecialist] = {}

    async def analyze(self, payload: AnalysisJobCreate) -> AnalysisReport:
        normalized_payload, evidence = self._normalize_logs(payload)
        code_context = self.retriever.retrieve(normalized_payload)
        specialist = self._deploy_specialist(normalized_payload.service_name)

        try:
            report = await specialist.diagnose(normalized_payload, evidence, code_context)
        except (GeminiClientError, ValidationError, ValueError) as exc:
            logger.info(
                "Specialist diagnosis failed for service=%s, falling back: %s",
                normalized_payload.service_name,
                exc,
            )
            report = build_fallback_report(normalized_payload, evidence, code_context, reason=str(exc))

        service_kb.append_entry(normalized_payload.service_name, self._build_kb_entry(normalized_payload, report))
        return report

    def _deploy_specialist(self, service_name: str) -> ServiceSpecialist:
        specialist = self._specialists.get(service_name)
        if specialist is None:
            specialist = ServiceSpecialist(service_name)
            self._specialists[service_name] = specialist
        return specialist

    def _normalize_logs(self, payload: AnalysisJobCreate) -> tuple[AnalysisJobCreate, list[EvidenceItem]]:
        trimmed = payload.model_copy(deep=True)
        trimmed.log_snippets = trimmed.log_snippets[: self.settings.max_log_snippets]

        evidence: list[EvidenceItem] = []
        for snippet in trimmed.log_snippets:
            line = snippet.line[: self.settings.max_log_line_chars]
            evidence.append(
                EvidenceItem(
                    type="log_snippet",
                    source=snippet.source,
                    snippet=line,
                    timestamp=snippet.timestamp,
                )
            )

        return trimmed, evidence

    def _build_kb_entry(self, payload: AnalysisJobCreate, report: AnalysisReport) -> str:
        problems = _extract_section_bullets(report.summary_text, "Problems Found", limit=3)
        actions = _extract_section_bullets(report.summary_text, "Solution Suggestions", limit=3)

        lines = [
            f"## Incident {payload.detected_at.isoformat()} — {payload.incident_id} ({report.status})",
            f"- Node: {payload.device_or_node}",
        ]
        if problems:
            lines.append("- Problems found:")
            lines.extend(f"  - {line}" for line in problems)
        if actions:
            lines.append("- Suggested actions:")
            lines.extend(f"  - {line}" for line in actions)
        if report.fallback_reason:
            lines.append(f"- Fallback reason: {report.fallback_reason}")

        return "\n".join(lines)
