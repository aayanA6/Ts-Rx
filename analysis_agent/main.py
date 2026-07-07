from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from analysis_agent.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)
from analysis_agent.config import get_settings
from analysis_agent.database import SessionLocal, engine, get_db
from analysis_agent.models import (
    AnalysisJob,
    AnalysisReport,
    ApiKey,
    Base,
    JobStatus,
    NotificationSettings,
    ReportStatus,
    User,
)
from analysis_agent.schemas import (
    AnalysisJobCreate,
    ApiKeyCreateRequest,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    DeviceHealthView,
    IncidentView,
    IngestPayload,
    IngestResponse,
    JobCreatedResponse,
    JobStatusResponse,
    LoginRequest,
    NotificationSettingsRequest,
    NotificationSettingsResponse,
    ProposedFixView,
    RefreshRequest,
    RegisterRequest,
    ServiceSummary,
    SummaryResponse,
    TailscaleDeviceRaw,
    TokenResponse,
    UptimeKumaJobCreate,
    UptimeStatus,
    UserResponse,
)
from analysis_agent.limiter import check_auth_rate_limit
from analysis_agent.tailscale_client import TailscaleClientError, get_tailscale_client
from analysis_agent.worker import AnalysisWorker, set_redis

settings = get_settings()
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s",
)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


for handler in logging.getLogger().handlers:
    handler.addFilter(RequestIdFilter())

logger = logging.getLogger(__name__)
app = FastAPI(title="ts-rx", version="1.0.0")
worker_task: asyncio.Task | None = None
worker: AnalysisWorker | None = None
redis_client = None

bearer_scheme = HTTPBearer(auto_error=False)

def _build_cors_origins() -> list[str]:
    origins: set[str] = {settings.app_url.rstrip("/")}
    for extra in settings.cors_origins.split(","):
        extra = extra.strip().rstrip("/")
        if extra:
            origins.add(extra)
    return sorted(origins)


app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def inject_request_id(request: Request, call_next):
    rid = request.headers.get("x-request-id", str(uuid.uuid4()))
    token = request_id_ctx.set(rid)
    try:
        response = await call_next(request)
    finally:
        request_id_ctx.reset(token)
    response.headers["X-Request-ID"] = rid
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"message": "Malformed payload", "detail": exc.errors()})


_DEFAULT_JWT_SECRET = "change-me-in-production-use-a-long-random-string"


@app.on_event("startup")
async def on_startup() -> None:
    global redis_client

    if settings.jwt_secret == _DEFAULT_JWT_SECRET:
        if settings.environment == "production":
            raise RuntimeError(
                "JWT_SECRET is set to the insecure default. "
                "Generate one with: openssl rand -hex 64"
            )
        logger.warning(
            "⚠️  JWT_SECRET is the insecure default — acceptable in dev only. "
            "Set JWT_SECRET before deploying to production."
        )

    # Schema management: create_all is idempotent for new tables but does NOT
    # apply ALTER TABLE for column additions. For schema changes on an existing
    # database, recreate the database or apply the DDL manually.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Redis (optional — gracefully degrade if unavailable)
    try:
        import redis.asyncio as aioredis
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        set_redis(redis_client)
        logger.info("Redis connected")
    except Exception as exc:
        logger.warning("Redis unavailable — WebSocket events disabled: %s", exc)
        redis_client = None

    global worker, worker_task
    if settings.worker_enabled:
        worker = AnalysisWorker(SessionLocal, poll_interval_sec=settings.worker_poll_interval_sec)
        worker_task = asyncio.create_task(worker.run())
        logger.info("Worker started")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global worker_task, worker, redis_client
    if worker is not None:
        await worker.stop()
    if worker_task is not None:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    if redis_client is not None:
        await redis_client.aclose()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = decode_token(credentials.credentials, expected_type="access")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def get_user_by_api_key(api_key_header: str, db: AsyncSession) -> User:
    key_hash = hash_api_key(api_key_header)
    result = await db.execute(
        select(ApiKey).options(selectinload(ApiKey.user)).where(ApiKey.key_hash == key_hash)
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    # Update last_used_at
    api_key.last_used_at = datetime.now(tz=timezone.utc)
    await db.commit()
    return api_key.user


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.post("/auth/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db), _rl: None = Depends(check_auth_rate_limit)) -> TokenResponse:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=body.email, hashed_password=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@app.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db), _rl: None = Depends(check_auth_rate_limit)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user_id = decode_token(body.refresh_token, expected_type="refresh")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@app.get("/auth/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=current_user.id, email=current_user.email, created_at=current_user.created_at)


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

@app.get("/api/v1/keys", response_model=list[ApiKeyResponse])
async def list_api_keys(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiKey).where(ApiKey.user_id == current_user.id).order_by(ApiKey.created_at))
    keys = result.scalars().all()
    return [ApiKeyResponse(id=k.id, label=k.label, created_at=k.created_at, last_used_at=k.last_used_at) for k in keys]


@app.post("/api/v1/keys", response_model=ApiKeyCreatedResponse, status_code=201)
async def create_api_key(
    body: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreatedResponse:
    plaintext, hashed = generate_api_key()
    key = ApiKey(user_id=current_user.id, key_hash=hashed, label=body.label)
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return ApiKeyCreatedResponse(id=key.id, label=key.label, key=plaintext, created_at=key.created_at)


@app.delete("/api/v1/keys/{key_id}", status_code=204)
async def delete_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == current_user.id))
    key = result.scalar_one_or_none()
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.delete(key)
    await db.commit()


# ---------------------------------------------------------------------------
# Notification settings
# ---------------------------------------------------------------------------

@app.get("/api/v1/notifications", response_model=NotificationSettingsResponse)
async def get_notifications(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NotificationSettings).where(NotificationSettings.user_id == current_user.id))
    notif = result.scalar_one_or_none()
    if notif is None:
        return NotificationSettingsResponse(
            email_enabled=False, discord_enabled=False, discord_webhook_url=None,
            slack_enabled=False, slack_webhook_url=None,
        )
    return NotificationSettingsResponse(
        email_enabled=notif.email_enabled,
        discord_enabled=notif.discord_enabled,
        discord_webhook_url=notif.discord_webhook_url,
        slack_enabled=notif.slack_enabled,
        slack_webhook_url=notif.slack_webhook_url,
    )


@app.put("/api/v1/notifications", response_model=NotificationSettingsResponse)
async def update_notifications(
    body: NotificationSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationSettingsResponse:
    result = await db.execute(select(NotificationSettings).where(NotificationSettings.user_id == current_user.id))
    notif = result.scalar_one_or_none()
    if notif is None:
        notif = NotificationSettings(user_id=current_user.id)
        db.add(notif)

    notif.email_enabled = body.email_enabled
    notif.discord_enabled = body.discord_enabled
    notif.discord_webhook_url = body.discord_webhook_url
    notif.slack_enabled = body.slack_enabled
    notif.slack_webhook_url = body.slack_webhook_url
    await db.commit()

    return NotificationSettingsResponse(
        email_enabled=notif.email_enabled,
        discord_enabled=notif.discord_enabled,
        discord_webhook_url=notif.discord_webhook_url,
        slack_enabled=notif.slack_enabled,
        slack_webhook_url=notif.slack_webhook_url,
    )


# ---------------------------------------------------------------------------
# Webhook ingest (no JWT — API key in header or path)
# ---------------------------------------------------------------------------

def _normalize_ingest(raw: dict) -> IngestPayload:
    """Accept both our flat format and Uptime Kuma's nested heartbeat/monitor format."""
    if "heartbeat" in raw:
        hb = raw["heartbeat"]
        mon = raw.get("monitor", {})
        monitor_name = hb.get("monitorName") or (mon.get("name") if isinstance(mon, dict) else None) or "unknown"
        status_str = hb.get("status", "")
        # Uptime Kuma uses 0/1 integers or "up"/"down" strings
        if isinstance(status_str, int):
            status_str = "UP" if status_str == 1 else "DOWN"
        msg = hb.get("msg", "")
        url = (mon.get("url", "") if isinstance(mon, dict) else "") or ""
        ts = hb.get("time") or datetime.now(tz=timezone.utc).isoformat()
        return IngestPayload(
            monitor=monitor_name,
            status=status_str,
            msg=msg,
            url=url,
            time=ts,
        )
    return IngestPayload.model_validate(raw)


@app.post("/api/v1/ingest/{api_key}", response_model=IngestResponse)
async def ingest_webhook(
    api_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    try:
        raw = await request.json()
        payload = _normalize_ingest(raw)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Malformed payload: {exc}") from exc
    user = await get_user_by_api_key(api_key, db)
    status_norm = payload.status.strip().upper()

    if status_norm == "UP":
        # Resolve open incidents for this monitor
        result = await db.execute(
            select(AnalysisJob).where(
                AnalysisJob.user_id == user.id,
                AnalysisJob.resolved == False,  # noqa: E712
                AnalysisJob.request_payload["service_name"].as_string() == payload.monitor,
            ).order_by(AnalysisJob.created_at.desc()).limit(10)
        )
        jobs = result.scalars().all()
        for job in jobs:
            job.resolved = True
            job.resolved_at = datetime.now(tz=timezone.utc)
        await db.commit()

        if redis_client and jobs:
            for job in jobs:
                await redis_client.publish(
                    f"user:{user.id}:events",
                    json.dumps({"type": "incident_resolved", "incident_id": job.incident_id, "job_id": str(job.id)}),
                )

        return IngestResponse(action="resolved", message=f"Resolved {len(jobs)} incident(s) for {payload.monitor}")

    if status_norm not in {"DOWN", "DEGRADED"}:
        return IngestResponse(action="ignored", message=f"Status {payload.status!r} ignored")

    # Create analysis job
    import hashlib as _hashlib
    from urllib.parse import urlparse
    node = payload.metadata.get("device_or_node") or payload.metadata.get("node") or urlparse(payload.url).hostname or "unknown"
    base = f"{payload.monitor}|{payload.time.isoformat()}|{status_norm}"
    digest = _hashlib.sha1(base.encode()).hexdigest()[:12]
    slug = "".join(ch if ch.isalnum() else "-" for ch in payload.monitor.lower()).strip("-")[:40] or "monitor"
    incident_id = f"inc-{slug}-{digest}"
    idempotency_key = f"{user.id}:{incident_id}"

    existing = await db.execute(select(AnalysisJob).where(AnalysisJob.idempotency_key == idempotency_key))
    existing_job = existing.scalar_one_or_none()
    if existing_job:
        return IngestResponse(action="queued", job_id=existing_job.id, message="Duplicate — existing job returned")

    internal = AnalysisJobCreate(
        incident_id=incident_id,
        service_name=payload.monitor,
        device_or_node=str(node),
        uptime_status=UptimeStatus(status_norm.lower()),
        uptime_description=payload.msg or f"{payload.monitor} is {status_norm}",
        detected_at=payload.time,
        log_snippets=payload.log_snippets,
        metadata=payload.metadata,
        idempotency_key=idempotency_key,
    )

    job = AnalysisJob(
        user_id=user.id,
        incident_id=incident_id,
        idempotency_key=idempotency_key,
        status=JobStatus.queued.value,
        progress=0,
        request_payload=internal.model_dump(mode="json"),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return IngestResponse(action="queued", job_id=job.id, message="Analysis job created")


# ---------------------------------------------------------------------------
# Analysis routes (authenticated)
# ---------------------------------------------------------------------------

@app.post("/api/v1/analysis/jobs", response_model=JobCreatedResponse)
async def create_job(
    payload: UptimeKumaJobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobCreatedResponse:
    normalized = payload.to_internal()
    if normalized.idempotency_key:
        existing = await db.execute(select(AnalysisJob).where(AnalysisJob.idempotency_key == normalized.idempotency_key))
        existing_job = existing.scalar_one_or_none()
        if existing_job:
            return JobCreatedResponse(job_id=existing_job.id, status=existing_job.status.value)

    job = AnalysisJob(
        user_id=current_user.id,
        incident_id=normalized.incident_id,
        idempotency_key=normalized.idempotency_key,
        status=JobStatus.queued.value,
        progress=0,
        request_payload=normalized.model_dump(mode="json"),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return JobCreatedResponse(job_id=job.id, status=job.status.value)


async def _fetch_incident_views(
    current_user: User,
    db: AsyncSession,
    include_resolved: bool = False,
    limit: int = 50,
) -> list[IncidentView]:
    safe_limit = min(max(limit, 1), 200)
    stmt = (
        select(AnalysisJob, AnalysisReport)
        .outerjoin(AnalysisReport, AnalysisReport.job_id == AnalysisJob.id)
        .where(AnalysisJob.user_id == current_user.id)
        .order_by(AnalysisJob.created_at.desc())
        .limit(safe_limit)
    )
    if not include_resolved:
        stmt = stmt.where(AnalysisJob.resolved == False)  # noqa: E712

    rows = await db.execute(stmt)

    output: list[IncidentView] = []
    for job, report in rows.all():
        payload = job.request_payload or {}
        report_json = (report.report_json if report else {}) or {}
        metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}

        service_name = str(payload.get("service_name", "unknown-service"))
        uptime_status = str(payload.get("uptime_status", "")).lower()
        ui_status = _map_job_to_ui_status(job.status, uptime_status, job.resolved)
        logs = _extract_logs(payload, report_json)
        confidence = float(report.confidence) if report else 0.0
        device_or_node = str(payload.get("device_or_node", "")).strip() or None
        proposed_fix = _extract_proposed_fix(report, report_json, service_name, device_or_node)

        output.append(
            IncidentView(
                id=job.incident_id,
                service=service_name,
                serviceType=str(metadata.get("service_type", "service")),
                status=ui_status,
                logs=logs,
                confidence=max(0.0, min(1.0, confidence)),
                proposedFix=proposed_fix,
                jobId=str(job.id),
                detectedAt=job.created_at,
            )
        )

    return output


@app.get("/api/v1/analysis/incidents", response_model=list[IncidentView])
async def list_incidents(
    limit: int = 50,
    include_resolved: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[IncidentView]:
    return await _fetch_incident_views(current_user, db, include_resolved, limit)


@app.get("/api/v1/analysis/services", response_model=list[ServiceSummary])
async def list_services(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ServiceSummary]:
    result = await db.execute(
        select(AnalysisJob)
        .where(AnalysisJob.user_id == current_user.id)
        .order_by(AnalysisJob.created_at.desc())
        .limit(500)
    )
    jobs = result.scalars().all()

    # Aggregate by service name
    seen: dict[str, ServiceSummary] = {}
    for job in jobs:
        payload = job.request_payload or {}
        service_name = str(payload.get("service_name", "unknown-service"))
        metadata = payload.get("metadata", {}) or {}
        uptime_status = str(payload.get("uptime_status", "")).lower()
        ui_status = _map_job_to_ui_status(job.status, uptime_status, job.resolved)

        if service_name not in seen:
            seen[service_name] = ServiceSummary(
                service=service_name,
                serviceType=str(metadata.get("service_type", "service")),
                last_seen=job.created_at,
                incident_count=1,
                last_status=ui_status,
            )
        else:
            seen[service_name].incident_count += 1
            if job.created_at > seen[service_name].last_seen:
                seen[service_name].last_seen = job.created_at
                seen[service_name].last_status = ui_status

    return list(seen.values())


def _match_device_to_incident(name: str, hostname: str, incidents: list[IncidentView]) -> IncidentView | None:
    short_host = hostname.split(".")[0].lower() if hostname else ""
    haystacks = {h for h in (name.lower(), hostname.lower(), short_host) if h}
    for incident in incidents:
        needles = {incident.service.lower()}
        if incident.proposedFix and incident.proposedFix.targetNode:
            needles.add(incident.proposedFix.targetNode.lower())
        for needle in needles:
            if needle and any(needle in hay or hay in needle for hay in haystacks):
                return incident
    return None


@app.get("/api/v1/tailscale/devices", response_model=list[DeviceHealthView])
async def list_device_health(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DeviceHealthView]:
    try:
        raw_devices = await get_tailscale_client().list_devices()
    except TailscaleClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    incidents = await _fetch_incident_views(current_user, db, include_resolved=False, limit=200)

    output: list[DeviceHealthView] = []
    for raw in raw_devices:
        parsed = TailscaleDeviceRaw.model_validate(raw)
        matched = _match_device_to_incident(parsed.name, parsed.hostname, incidents)
        output.append(
            DeviceHealthView(
                id=parsed.id,
                name=parsed.name,
                hostname=parsed.hostname,
                addresses=parsed.addresses,
                os=parsed.os,
                lastSeen=parsed.lastSeen,
                status=matched.status if matched else ("online" if parsed.connectedToControl else "offline"),
                incident=matched,
            )
        )
    return output


@app.get("/api/v1/analysis/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id, AnalysisJob.user_id == current_user.id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        progress=job.progress,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@app.get("/api/v1/analysis/jobs/{job_id}/result")
async def get_result(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(AnalysisReport)
        .join(AnalysisJob, AnalysisJob.id == AnalysisReport.job_id)
        .where(AnalysisReport.job_id == job_id, AnalysisJob.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        job_result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id, AnalysisJob.user_id == current_user.id))
        job = job_result.scalar_one_or_none()
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status in {JobStatus.queued.value, JobStatus.running.value}:
            raise HTTPException(status_code=409, detail="Job still processing")
        raise HTTPException(status_code=404, detail="Report not found")

    return report.report_json


@app.get("/api/v1/analysis/jobs/{job_id}/summary", response_model=SummaryResponse)
async def get_summary(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SummaryResponse:
    result = await db.execute(
        select(AnalysisReport)
        .join(AnalysisJob, AnalysisJob.id == AnalysisReport.job_id)
        .where(AnalysisReport.job_id == job_id, AnalysisJob.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return SummaryResponse(incident_id=report.incident_id, summary_text=report.summary_text, confidence=report.confidence)


@app.get("/api/v1/analysis/jobs/{job_id}/download")
async def download_report(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    result = await db.execute(
        select(AnalysisReport)
        .join(AnalysisJob, AnalysisJob.id == AnalysisReport.job_id)
        .where(AnalysisReport.job_id == job_id, AnalysisJob.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    content = json.dumps(report.report_json, indent=2).encode("utf-8")
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="analysis-report-{job_id}.json"'},
    )


@app.post("/api/v1/analysis/incidents/{incident_id}/resolve", status_code=204)
async def resolve_incident(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(AnalysisJob)
        .where(
            AnalysisJob.incident_id == incident_id,
            AnalysisJob.user_id == current_user.id,
            AnalysisJob.resolved == False,  # noqa: E712
        )
        .order_by(AnalysisJob.created_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Incident not found or already resolved")
    job.resolved = True
    job.resolved_at = datetime.now(tz=timezone.utc)
    await db.commit()
    if redis_client:
        await redis_client.publish(
            f"user:{current_user.id}:events",
            json.dumps({"type": "incident_resolved", "incident_id": incident_id, "job_id": str(job.id)}),
        )


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws/incidents")
async def ws_incidents(websocket: WebSocket, token: str | None = None) -> None:
    user_id = decode_token(token or "", expected_type="access") if token else None
    if user_id is None:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    if redis_client is None:
        # No Redis — keep connection alive but send nothing
        try:
            while True:
                await asyncio.sleep(30)
                await websocket.send_json({"type": "ping"})
        except (WebSocketDisconnect, Exception):
            return

    channel = f"user:{user_id}:events"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await websocket.send_json(data)
                except Exception:
                    pass
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()


# ---------------------------------------------------------------------------
# Health / root
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "time": datetime.now(tz=timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _map_job_to_ui_status(job_status: str, uptime_status: str, resolved: bool = False) -> str:
    if resolved:
        return "resolved"
    if job_status in {JobStatus.queued.value, JobStatus.running.value}:
        return "resolving"
    if job_status == JobStatus.failed.value:
        return "warning"
    if uptime_status == "degraded":
        return "warning"
    return "issue"


def _extract_logs(payload: dict[str, Any], report_json: dict[str, Any]) -> list[str]:
    evidence_items = report_json.get("evidence", [])
    if isinstance(evidence_items, list) and evidence_items:
        logs = [str(item.get("snippet", "")) for item in evidence_items if isinstance(item, dict)]
        logs = [line for line in logs if line]
        if logs:
            return logs[:12]

    raw_logs = payload.get("log_snippets", [])
    if isinstance(raw_logs, list):
        logs = [str(item.get("line", "")) for item in raw_logs if isinstance(item, dict)]
        logs = [line for line in logs if line]
        if logs:
            return logs[:12]

    description = str(payload.get("uptime_description", "No logs provided"))
    return [description]


_DESTRUCTIVE_RE = re.compile(
    r"\b(rm\b|rmdir|kill\b|pkill|killall|DROP\b|TRUNCATE\b|DELETE\b|mkfs|dd\b|wipe\b|purge\b|shred\b)",
    re.IGNORECASE,
)


def _find_destructive_steps(steps: list[str]) -> list[str]:
    return [step for step in steps if _DESTRUCTIVE_RE.search(step)]


def _extract_proposed_fix(
    report: AnalysisReport | None,
    report_json: dict[str, Any],
    service_name: str,
    device_or_node: str | None = None,
) -> ProposedFixView | None:
    if report is None:
        return None

    summary = _select_summary_text(report.summary_text, report_json, service_name)
    suggested_actions = report_json.get("suggested_actions", [])
    steps: list[str] = []

    if isinstance(suggested_actions, list):
        for item in suggested_actions:
            if not isinstance(item, dict):
                continue
            step = _normalize_step_from_action(item)
            if step:
                steps.append(step)

    if not steps:
        steps = _extract_solution_steps(summary)
    steps = _dedupe_steps(steps)
    if not steps:
        return None

    target = (device_or_node or "").strip() or None
    destructive = _find_destructive_steps(steps) or None

    return ProposedFixView(
        description=summary,
        markdown=summary,
        steps=steps[:8],
        destructiveActions=destructive,
        targetNode=target,
    )


def _select_summary_text(raw_summary: str, report_json: dict[str, Any], service_name: str) -> str:
    summary = str(raw_summary or "").strip()
    if _has_required_sections(summary):
        return summary
    if not _is_low_quality_summary(summary):
        return _build_summary_fallback(report_json, service_name, summary)
    return _build_summary_fallback(report_json, service_name)


def _has_required_sections(summary: str) -> bool:
    normalized = " ".join(summary.lower().split())
    required_sections = ("investigation steps", "problems found", "other important info", "solution suggestions")
    return all(section in normalized for section in required_sections)


def _is_low_quality_summary(summary: str) -> bool:
    normalized = " ".join(summary.lower().split())
    if not normalized:
        return True
    weak_markers = (
        "without a structured report",
        "manual triage",
        "no structured actions",
        "triage generated without concise summary",
        "insufficient structured",
        "insufficient evidence",
        "fallback triage:",
    )
    return any(marker in normalized for marker in weak_markers)


def _build_summary_fallback(report_json: dict[str, Any], service_name: str, base_summary: str = "") -> str:
    hypotheses = _extract_top_hypotheses(report_json)
    evidence = _extract_evidence_highlights(report_json)
    lines = [
        "## Investigation Steps",
        f"- Diagnosis markdown was not provided for **{service_name}**.",
        "- Built this summary from available hypotheses and evidence in the report payload.",
        "",
        "## Problems Found",
    ]
    if base_summary:
        lines.append(f"- {_truncate_line(base_summary)}")
    if hypotheses:
        lines.extend(hypotheses)
    if evidence:
        lines += ["", "## Other Important Info", "- Evidence highlights:"] + evidence
    else:
        lines += ["", "## Other Important Info", "- No additional evidence highlights were available in this report."]
    lines += ["", "## Solution Suggestions", "- Use the execution plan below to validate or rule out these hypotheses."]
    return "\n".join(lines)


def _extract_top_hypotheses(report_json: dict[str, Any]) -> list[str]:
    items = report_json.get("root_cause_hypotheses", [])
    if not isinstance(items, list):
        return []
    output: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        hypothesis = str(item.get("hypothesis", "")).strip()
        if not hypothesis:
            continue
        confidence = _parse_confidence_percent(item.get("confidence"))
        output.append(f"- {hypothesis} ({confidence}% confidence)" if confidence is not None else f"- {hypothesis}")
        if len(output) >= 2:
            break
    return output


def _extract_evidence_highlights(report_json: dict[str, Any]) -> list[str]:
    items = report_json.get("evidence", [])
    if not isinstance(items, list):
        return []
    output: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        snippet = str(item.get("snippet", "")).strip()
        if not snippet:
            continue
        output.append(f"- {_truncate_line(snippet)}")
        if len(output) >= 2:
            break
    return output


def _parse_confidence_percent(value: Any) -> int | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    numeric = max(0.0, min(numeric if numeric > 1 else numeric * 100, 100))
    return int(round(numeric))


def _truncate_line(text: str, max_len: int = 180) -> str:
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= max_len else f"{normalized[: max_len - 3].rstrip()}..."


def _normalize_step_from_action(item: dict[str, Any]) -> str:
    command = str(item.get("suggested_command", "")).strip()
    description = str(item.get("description", "")).strip()
    title = str(item.get("title", "")).strip()
    placeholder_markers = ("# manual investigation command", "# inspect logs and service health manually")
    normalized_command = command.lower()
    candidates: list[str] = []
    if command and all(marker not in normalized_command for marker in placeholder_markers):
        candidates.append(command)
    candidates.extend([description, title])
    for candidate in candidates:
        cleaned = _clean_step_text(candidate)
        if cleaned:
            return cleaned
    return ""


def _extract_solution_steps(summary: str) -> list[str]:
    if not summary.strip():
        return []
    pattern = r"##\s*Solution Suggestions\s*(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, summary, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    body = match.group(1)
    steps: list[str] = []
    for raw_line in body.splitlines():
        cleaned = _clean_step_text(raw_line)
        if not cleaned:
            continue
        steps.append(cleaned)
        if len(steps) >= 8:
            break
    return steps


def _clean_step_text(value: str) -> str:
    text = " ".join(str(value).split()).strip()
    if not text:
        return ""
    text = re.sub(r"^[-*]\s+", "", text)
    text = re.sub(r"^\d+\.\s+", "", text).strip()
    text = text.replace("**", "").strip()
    lower = text.lower()
    if lower.startswith("manual-only text:"):
        text = text.split(":", 1)[1].strip()
    elif lower.startswith("manual only text:"):
        text = text.split(":", 1)[1].strip()
    if lower.startswith("safety note:") or "do not execute automatically" in lower:
        return ""
    if text.endswith(":"):
        text = text[:-1].strip()
    return text


def _dedupe_steps(steps: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for step in steps:
        normalized = " ".join(step.lower().split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(step)
    return deduped
