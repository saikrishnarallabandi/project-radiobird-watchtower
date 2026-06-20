from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class MetricRule:
    baseline: float
    direction: str


@dataclass(frozen=True)
class Asset:
    id: str
    name: str
    theme: str
    location: str
    tickers: list[str]
    metrics: dict[str, MetricRule]
    latitude: float | None = None
    longitude: float | None = None
    bbox: dict[str, float] = field(default_factory=dict)
    cadence_minutes: int = 60
    providers: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Observation:
    asset_id: str
    source: str
    metric: str
    value: float
    unit: str = ""
    observed_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Anomaly:
    asset_id: str
    source: str
    metric: str
    value: float
    baseline: float
    severity: str
    confidence: float
    reason: str
    observed_at: str
    created_at: str = field(default_factory=utc_now_iso)
