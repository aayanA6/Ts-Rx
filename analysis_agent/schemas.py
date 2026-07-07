from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime


class ApiKeyCreateRequest(BaseModel):
    label: str = Field(default="Default", min_length=1, max_length=100)


class ApiKeyResponse(BaseModel):
    id: UUID
    label: str
    created_at: datetime
    last_used_at: datetime | None = None


class ApiKeyCreatedResponse(BaseModel):
    id: UUID
    label: str
    key: str  # plaintext — returned only once
    created_at: datetime


class NotificationSettingsRequest(BaseModel):
    email_enabled: bool = False
    discord_enabled: bool = False
    discord_webhook_url: str | None = Field(default=None, max_length=500)
    slack_enabled: bool = False
    slack_webhook_url: str | None = Field(default=None, max_length=500)


class NotificationSettingsResponse(BaseModel):
    email_enabled: bool
    discord_enabled: bool
    discord_webhook_url: str | None
    slack_enabled: bool
    slack_webhook_url: str | None


# ---------------------------------------------------------------------------
# Incident / Job schemas (existing + extended)
# ---------------------------------------------------------------------------

class UptimeStatus(str, Enum):
    down = "down"
    degraded = "degraded"


class LogSnippet(BaseModel):
    timestamp: datetime
    source: str = Field(min_length=1, max_length=400)
    line: str = Field(min_length=1, max_length=20000)


class AnalysisJobCreate(BaseModel):
    incident_id: str = Field(min_length=1, max_length=200)
    service_name: str = Field(min_length=1, max_length=200)
    device_or_node: str = Field(min_length=1, max_length=200)
    uptime_status: UptimeStatus
    uptime_description: str = Field(min_length=1, max_length=4000)
    detected_at: datetime
    log_snippets: list[LogSnippet] = Field(default_factory=list, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)


class UptimeKumaJobCreate(BaseModel):
    monitor: str = Field(min_length=1, max_length=200)
    status: str = Field(min_length=1, max_length=40)
    msg: str = Field(min_length=1, max_length=4000)
    url: str = Field(min_length=1, max_length=2000)
    time: datetime
    log_snippets: list[LogSnippet] = Field(default_factory=list, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {UptimeStatus.down.value, UptimeStatus.degraded.value}:
            raise ValueError("status must be DOWN/down or DEGRADED/degraded for triage jobs")
        return normalized

    def to_internal(self) -> AnalysisJobCreate:
        node = (
            self.metadata.get("device_or_node")
            or self.metadata.get("node")
            or self._node_from_url(self.url)
            or "unknown-node"
        )
        incident_id = self._incident_id()
        return AnalysisJobCreate(
            incident_id=incident_id,
            service_name=self.monitor,
            device_or_node=str(node),
            uptime_status=UptimeStatus(self.status),
            uptime_description=self.msg,
            detected_at=self.time,
            log_snippets=self.log_snippets,
            metadata=self.metadata,
            idempotency_key=self.idempotency_key,
        )

    def _incident_id(self) -> str:
        base = f"{self.monitor}|{self.time.isoformat()}|{self.status}"
        digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]
        slug = "".join(ch if ch.isalnum() else "-" for ch in self.monitor.lower()).strip("-")
        slug = slug[:40] or "monitor"
        return f"inc-{slug}-{digest}"

    def _node_from_url(self, value: str) -> str | None:
        parsed = urlparse(value)
        return parsed.hostname


class IngestPayload(BaseModel):
    """Flexible payload for the /ingest endpoint — accepts UP for resolution too."""
    monitor: str = Field(min_length=1, max_length=200)
    status: str = Field(min_length=1, max_length=40)
    msg: str = Field(default="", max_length=4000)
    url: str = Field(default="", max_length=2000)
    time: datetime
    log_snippets: list[LogSnippet] = Field(default_factory=list, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    action: Literal["queued", "resolved", "ignored"]
    job_id: UUID | None = None
    message: str = ""


class JobCreatedResponse(BaseModel):
    job_id: UUID
    status: str


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: str
    progress: int
    error: str | None
    created_at: datetime
    updated_at: datetime


class ProposedFixView(BaseModel):
    description: str
    steps: list[str]
    markdown: str | None = None
    destructiveActions: list[str] | None = None
    targetNode: str | None = None


class IncidentView(BaseModel):
    id: str
    service: str
    serviceType: str
    status: Literal["online", "issue", "warning", "resolving", "resolved"]
    logs: list[str]
    confidence: float = Field(ge=0, le=1)
    proposedFix: ProposedFixView | None = None
    jobId: str | None = None
    detectedAt: datetime | None = None


class ServiceSummary(BaseModel):
    service: str
    serviceType: str
    last_seen: datetime
    incident_count: int
    last_status: str


class TailscaleDeviceRaw(BaseModel):
    """Subset of fields from Tailscale's GET /tailnet/{tailnet}/devices response."""
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    hostname: str = ""
    addresses: list[str] = Field(default_factory=list)
    os: str = ""
    lastSeen: datetime | None = None
    connectedToControl: bool = False


class DeviceHealthView(BaseModel):
    id: str
    name: str
    hostname: str
    addresses: list[str] = Field(default_factory=list)
    os: str = ""
    lastSeen: datetime | None = None
    status: Literal["online", "issue", "warning", "resolving", "resolved", "offline"] = "online"
    incident: IncidentView | None = None


class Hypothesis(BaseModel):
    hypothesis: str
    confidence: float = Field(ge=0, le=1)
    evidence_refs: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    type: str
    source: str
    snippet: str
    timestamp: datetime | None = None


class CodeContextItem(BaseModel):
    file_path: str
    line_start: int
    line_end: int
    excerpt: str


class SuggestedAction(BaseModel):
    title: str
    description: str
    suggested_command: str
    safety_note: str


class ModelInfo(BaseModel):
    provider: str
    model_name: str
    latency_ms: int
    token_usage: dict[str, int] = Field(default_factory=dict)


class AnalysisReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str
    status: str
    root_cause_hypotheses: list[Hypothesis]
    evidence: list[EvidenceItem]
    code_context: list[CodeContextItem]
    suggested_actions: list[SuggestedAction]
    summary_text: str
    model: ModelInfo
    fallback_reason: str | None = None


class SummaryResponse(BaseModel):
    incident_id: str
    summary_text: str
    confidence: float
