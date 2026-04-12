import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime

from google.api_core.exceptions import PreconditionFailed

from app.config import Settings


@dataclass
class UsageDecision:
    allowed: bool
    daily_limit: int
    used_today: int
    remaining_generations: int


class DailyUsageLimiter:
    def __init__(self, settings: Settings):
        self.daily_limit = settings.daily_generation_limit
        self.bucket_name = settings.gcs_bucket_name
        self.client = None
        self._memory_counts: dict[str, int] = {}

        if self.bucket_name:
            from google.cloud import storage

            self.client = storage.Client(project=settings.google_cloud_project)

    def consume(self, client_identifier: str) -> UsageDecision:
        if self.daily_limit <= 0:
            return UsageDecision(
                allowed=True,
                daily_limit=self.daily_limit,
                used_today=0,
                remaining_generations=0
            )

        key = self._build_key(client_identifier)

        if not self.client:
            return self._consume_in_memory(key)

        return self._consume_in_gcs(key)

    def _build_key(self, client_identifier: str) -> str:
        digest = hashlib.sha256(client_identifier.encode("utf-8")).hexdigest()
        current_day = datetime.now(UTC).strftime("%Y-%m-%d")
        return f"usage-limits/{current_day}/{digest}.json"

    def _decision(self, used_today: int, allowed: bool) -> UsageDecision:
        remaining = max(self.daily_limit - used_today, 0)
        return UsageDecision(
            allowed=allowed,
            daily_limit=self.daily_limit,
            used_today=used_today,
            remaining_generations=remaining
        )

    def _consume_in_memory(self, key: str) -> UsageDecision:
        used_today = self._memory_counts.get(key, 0)
        if used_today >= self.daily_limit:
            return self._decision(used_today, allowed=False)

        updated_used_today = used_today + 1
        self._memory_counts[key] = updated_used_today
        return self._decision(updated_used_today, allowed=True)

    def _consume_in_gcs(self, key: str) -> UsageDecision:
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(key)

        for _ in range(5):
            if not blob.exists():
                payload = json.dumps({"count": 1}).encode("utf-8")
                try:
                    blob.upload_from_string(payload, content_type="application/json", if_generation_match=0)
                    return self._decision(1, allowed=True)
                except PreconditionFailed:
                    continue

            blob.reload()
            raw_payload = blob.download_as_bytes() or b"{}"
            data = json.loads(raw_payload.decode("utf-8"))
            used_today = int(data.get("count", 0))

            if used_today >= self.daily_limit:
                return self._decision(used_today, allowed=False)

            updated_used_today = used_today + 1
            payload = json.dumps({"count": updated_used_today}).encode("utf-8")

            try:
                blob.upload_from_string(
                    payload,
                    content_type="application/json",
                    if_generation_match=blob.generation
                )
                return self._decision(updated_used_today, allowed=True)
            except PreconditionFailed:
                continue

        raise RuntimeError("Could not update the daily generation limit. Please try again.")
