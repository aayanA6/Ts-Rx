from __future__ import annotations

import re
from pathlib import Path

from analysis_agent.config import get_settings

_SLUG_DISALLOWED = re.compile(r"[^a-z0-9._-]+")
_INCIDENT_HEADER = re.compile(r"\n(?=## Incident )")


def slugify(service_name: str) -> str:
    slug = _SLUG_DISALLOWED.sub("-", service_name.strip().lower()).strip("-")
    return slug[:120] or "unknown-service"


def kb_path(service_name: str) -> Path:
    settings = get_settings()
    kb_dir = (settings.project_root / settings.service_kb_dir).resolve()
    kb_dir.mkdir(parents=True, exist_ok=True)
    return kb_dir / f"{slugify(service_name)}.md"


def _starter_template(service_name: str) -> str:
    return (
        f"# Service Knowledge Base: {service_name}\n\n"
        "Accumulated incident history for this service. Auto-maintained by "
        "the orchestrator agent.\n\n"
        "_No incidents recorded yet._\n"
    )


def read_kb(service_name: str) -> str:
    path = kb_path(service_name)
    if not path.exists():
        return _starter_template(service_name)
    return path.read_text(encoding="utf-8", errors="ignore")


def append_entry(service_name: str, entry_markdown: str) -> None:
    settings = get_settings()
    path = kb_path(service_name)

    current = read_kb(service_name).replace("_No incidents recorded yet._\n", "").rstrip()
    updated = f"{current}\n\n{entry_markdown.strip()}\n"
    updated = _trim_to_budget(updated, settings.service_kb_max_chars)
    path.write_text(updated, encoding="utf-8")


def _trim_to_budget(content: str, max_chars: int) -> str:
    if len(content) <= max_chars:
        return content

    parts = _INCIDENT_HEADER.split(content)
    header, incidents = parts[0], parts[1:]

    # Drop oldest incident entries first until we're back under budget.
    while incidents and len("".join([header, *incidents])) > max_chars:
        incidents.pop(0)

    return "".join([header, *incidents])
