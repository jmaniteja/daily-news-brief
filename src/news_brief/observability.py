"""Small, public-safe metrics objects for a single brief generation run."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def _safe_error(exc: Exception) -> dict[str, str]:
    # Exception strings can contain URLs and, for badly behaved clients, response
    # fragments.  Reports deliberately retain only a short exception category.
    return {"category": type(exc).__name__.lower(), "message": type(exc).__name__[:120]}


@dataclass
class SourceMetrics:
    name: str
    type: str
    collection_started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    collection_duration_ms: int = 0
    request_count: int = 0
    http_statuses: dict[str, int] = field(default_factory=dict)
    response_bytes: int = 0
    entries_discovered: int = 0
    entries_malformed: int = 0
    entries_deduplicated: int = 0
    entries_shortlisted: int = 0
    article_fetch_attempts: int = 0
    article_extracted: int = 0
    article_excerpt_fallback: int = 0
    article_failures: int = 0
    article_http_failures: int = 0
    article_timeouts: int = 0
    article_unsupported_content: int = 0
    analysis_attempts: int = 0
    analysis_successes: int = 0
    analysis_irrelevant: int = 0
    analysis_malformed: int = 0
    analysis_retries: int = 0
    analysis_failures: int = 0
    selected: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)

    def request(self, response) -> None:
        self.request_count += 1
        status = getattr(response, "status_code", None)
        if status is not None:
            key = str(status)
            self.http_statuses[key] = self.http_statuses.get(key, 0) + 1
        content = getattr(response, "content", b"")
        self.response_bytes += len(content or b"")

    def error(self, exc: Exception) -> None:
        self.errors.append(_safe_error(exc))

    def to_dict(self) -> dict:
        return asdict(self)
