from __future__ import annotations

import json
from pathlib import Path

import requests

from .models import Asset, Observation, utc_now_iso


class Ingestor:
    name = "base"

    def ingest(self, assets: list[Asset]) -> list[Observation]:
        raise NotImplementedError


class FixtureIngestor(Ingestor):
    name = "fixture"

    def __init__(self, path: str | Path = "data/fixtures/supply_events.json") -> None:
        self.path = Path(path)

    def ingest(self, assets: list[Asset]) -> list[Observation]:
        asset_ids = {asset.id for asset in assets}
        raw = json.loads(self.path.read_text())
        observations: list[Observation] = []
        for item in raw:
            if item["asset_id"] not in asset_ids:
                continue
            observations.append(
                Observation(
                    asset_id=item["asset_id"],
                    source=item.get("source", self.name),
                    metric=item["metric"],
                    value=float(item["value"]),
                    unit=item.get("unit", ""),
                    observed_at=item.get("observed_at", utc_now_iso()),
                    metadata=item.get("metadata", {}),
                )
            )
        return observations


class WeatherIngestor(Ingestor):
    name = "weather"

    def ingest(self, assets: list[Asset]) -> list[Observation]:
        observations: list[Observation] = []
        for asset in assets:
            if "weather_risk" not in asset.metrics:
                continue
            risk, metadata = self._weather_risk(asset.location)
            observations.append(
                Observation(
                    asset_id=asset.id,
                    source=self.name,
                    metric="weather_risk",
                    value=risk,
                    unit="risk_score",
                    metadata=metadata,
                )
            )
        return observations

    def _weather_risk(self, location: str) -> tuple[float, dict[str, object]]:
        url = f"https://wttr.in/{location}?format=j1"
        try:
            response = requests.get(url, timeout=8)
            response.raise_for_status()
            data = response.json()
            current = data.get("current_condition", [{}])[0]
            desc = " ".join(x.get("value", "") for x in current.get("weatherDesc", []))
            wind_kmph = float(current.get("windspeedKmph", 0) or 0)
            precip_mm = float(current.get("precipMM", 0) or 0)
            risk = 0.0
            if wind_kmph >= 40:
                risk += 1.0
            if precip_mm >= 10:
                risk += 1.0
            risky_words = ("storm", "typhoon", "hurricane", "snow", "thunder", "fog")
            if any(word in desc.lower() for word in risky_words):
                risk += 1.0
            return min(risk, 3.0), {"description": desc, "wind_kmph": wind_kmph, "precip_mm": precip_mm}
        except Exception as exc:  # noqa: BLE001
            return 0.0, {"error": str(exc), "location": location}
