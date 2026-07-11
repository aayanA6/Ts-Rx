from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from analysis_agent.database import engine as _db_engine

from analysis_agent.models import AnalysisJob, AnalysisReport, JobStatus, ReportStatus
from analysis_agent.orchestrator import Orchestrator
from analysis_agent.schemas import AnalysisJobCreate
from analysis_agent.specialist import confidence_from_report

logger = logging.getLogger(__name__)

# Injected at startup by main.py when Redis is available
_redis_client = None


def set_redis(client) -> None:
    global _redis_client
    _redis_client = client


async def _publish_event(user_id: str | None, event: dict) -> None:
    if _redis_client is None or user_id is None:
        return
    try:
        channel = f"user:{user_id}:events"
        await _redis_client.publish(channel, json.dumps(event))
    except Exception as exc:
        logger.warning("Failed to publish WebSocket event: %s", exc)


class AnalysisWorker:
    def __init__(self, session_maker: async_sessionmaker, poll_interval_sec: float = 1.5) -> None:
        self._session_maker = session_maker
        self._poll_interval_sec = poll_interval_sec
        self._stop_event = asyncio.Event()
        self._orchestrator = Orchestrator()

    async def run(self) -> None:
        while not self._stop_event.is_set():
            job_id = await self._claim_next_job()
            if job_id is None:
                await asyncio.sleep(self._poll_interval_sec)
                continue

            try:
                await self._process_job(job_id)
            except Exception:  # noqa: BLE001
                logger.exception("Unhandled error while processing job %s", job_id)

    async def stop(self) -> None:
        self._stop_event.set()

    async def _claim_next_job(self) -> UUID | None:
        async with self._session_maker() as session:
            async with session.begin():
                stmt = (
                    select(AnalysisJob)
                    .where(AnalysisJob.status == JobStatus.queued.value)
                    .order_by(AnalysisJob.created_at)
                    .limit(1)
                )
                # SKIP LOCKED is PostgreSQL-only; not supported by SQLite
                if _db_engine.dialect.name == "postgresql":
                    stmt = stmt.with_for_update(skip_locked=True)

                result = await session.execute(stmt)
                job = result.scalar_one_or_none()
                if job is None:
                    return None

                job.status = JobStatus.running.value
                job.progress = 10
                job.started_at = datetime.now(tz=timezone.utc)
                return job.id

    async def _process_job(self, job_id: UUID) -> None:
        async with self._session_maker() as session:
            result = await session.execute(
                select(AnalysisJob)
                .where(AnalysisJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if job is None:
                return

            user_id = str(job.user_id) if job.user_id else None

            await _publish_event(user_id, {"type": "job_update", "job_id": str(job_id), "status": "running", "progress": 10})

            try:
                payload = AnalysisJobCreate.model_validate(job.request_payload)
                report = await self._orchestrator.analyze(payload)

                existing_report_result = await session.execute(select(AnalysisReport).where(AnalysisReport.job_id == job.id))
                db_report = existing_report_result.scalar_one_or_none()
                if db_report is None:
                    db_report = AnalysisReport(
                        job_id=job.id,
                        incident_id=payload.incident_id,
                        report_status=ReportStatus(report.status).value,
                        confidence=confidence_from_report(report),
                        summary_text=report.summary_text,
                        fallback_reason=report.fallback_reason,
                        model_info=report.model.model_dump(mode="json"),
                        report_json=report.model_dump(mode="json"),
                    )
                    session.add(db_report)
                else:
                    db_report.report_status = ReportStatus(report.status).value
                    db_report.confidence = confidence_from_report(report)
                    db_report.summary_text = report.summary_text
                    db_report.fallback_reason = report.fallback_reason
                    db_report.model_info = report.model.model_dump(mode="json")
                    db_report.report_json = report.model_dump(mode="json")

                job.status = JobStatus.completed.value
                job.progress = 100
                job.error = None
                job.finished_at = datetime.now(tz=timezone.utc)
                await session.commit()

                await _publish_event(user_id, {"type": "job_update", "job_id": str(job_id), "status": "completed", "progress": 100})

                # Send notifications
                await self._maybe_notify(job, db_report, payload.service_name)

            except Exception as exc:  # noqa: BLE001
                job.status = JobStatus.failed.value
                job.progress = 100
                job.error = str(exc)
                job.finished_at = datetime.now(tz=timezone.utc)
                logger.exception("Job %s failed", job_id)
                await session.commit()
                await _publish_event(user_id, {"type": "job_update", "job_id": str(job_id), "status": "failed", "progress": 100})

    async def _maybe_notify(self, job: AnalysisJob, report: AnalysisReport, service_name: str) -> None:
        if job.user_id is None:
            return
        try:
            from analysis_agent.notifier import send_incident_notification

            async with self._session_maker() as session:
                from sqlalchemy.orm import selectinload as sli
                from analysis_agent.models import NotificationSettings, User
                result = await session.execute(
                    select(NotificationSettings)
                    .options(sli(NotificationSettings.user))
                    .where(NotificationSettings.user_id == job.user_id)
                )
                notif = result.scalar_one_or_none()
                if notif is None:
                    return
                await send_incident_notification(
                    notif=notif,
                    service_name=service_name,
                    incident_id=report.incident_id,
                    confidence=report.confidence,
                    summary_text=report.summary_text,
                    job_id=str(job.id),
                )
        except Exception as exc:
            logger.warning("Notification failed for job %s: %s", job.id, exc)
