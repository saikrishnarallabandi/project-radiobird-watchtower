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
                    metadata={
                        "fixture": True,
                        "public_data_boundary": "Simulated/fixture data for MVP only; not a private feed.",
                        **item.get("metadata", {}),
                    },
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


class NoaaWeatherIngestor(Ingestor):
    """NOAA/NWS public weather adapter for US assets with latitude/longitude."""

    name = "weather_noaa"

    def __init__(self, session: requests.Session | None = None, timeout: int = 8) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout

    def ingest(self, assets: list[Asset]) -> list[Observation]:
        observations: list[Observation] = []
        for asset in assets:
            if "weather_risk" not in asset.metrics or asset.latitude is None or asset.longitude is None:
                continue
            risk, metadata = self._weather_risk(asset)
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

    def _weather_risk(self, asset: Asset) -> tuple[float, dict[str, object]]:
        try:
            points_url = f"https://api.weather.gov/points/{asset.latitude},{asset.longitude}"
            points = self._get_json(points_url)
            forecast_url = points["properties"]["forecastHourly"]
            forecast = self._get_json(forecast_url)
            period = forecast["properties"]["periods"][0]
            wind_mph = _parse_wind_mph(period.get("windSpeed", "0 mph"))
            short = str(period.get("shortForecast", ""))
            temperature = float(period.get("temperature", 0) or 0)
            risk = 0.0
            if wind_mph >= 35:
                risk += 1.0
            risky_words = ("storm", "thunder", "tornado", "hurricane", "snow", "ice", "fog")
            if any(word in short.lower() for word in risky_words):
                risk += 1.0
            if temperature <= 20 or temperature >= 100:
                risk += 0.5
            return min(risk, 3.0), {
                "provider": "NOAA/NWS public API",
                "location": asset.location,
                "forecast": short,
                "temperature": temperature,
                "wind_mph": wind_mph,
                "public_data_boundary": "Public NOAA/NWS endpoint; no auth and no non-public feed.",
            }
        except Exception as exc:  # noqa: BLE001
            return 0.0, {"error": str(exc), "location": asset.location, "provider": "NOAA/NWS public API"}

    def _get_json(self, url: str) -> dict:
        response = self.session.get(url, timeout=self.timeout, headers={"User-Agent": "radiobird-watchtower/0.1"})
        response.raise_for_status()
        return response.json()


class OpenSkyAdsbIngestor(Ingestor):
    """OpenSky public ADS-B adapter using anonymous states/all queries."""

    name = "adsb_opensky"

    def __init__(self, session: requests.Session | None = None, timeout: int = 8) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout

    def ingest(self, assets: list[Asset]) -> list[Observation]:
        observations: list[Observation] = []
        for asset in assets:
            if "cargo_flights" not in asset.metrics or not asset.bbox:
                continue
            count, metadata = self._count_aircraft(asset)
            observations.append(
                Observation(
                    asset_id=asset.id,
                    source=self.name,
                    metric="cargo_flights",
                    value=float(count),
                    unit="aircraft",
                    metadata=metadata,
                )
            )
        return observations

    def _count_aircraft(self, asset: Asset) -> tuple[int, dict[str, object]]:
        try:
            bbox = asset.bbox
            response = self.session.get(
                "https://opensky-network.org/api/states/all",
                params={
                    "lamin": bbox["lamin"],
                    "lomin": bbox["lomin"],
                    "lamax": bbox["lamax"],
                    "lomax": bbox["lomax"],
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            states = response.json().get("states") or []
            return len(states), {
                "provider": "OpenSky Network public states API",
                "bbox": bbox,
                "note": "Counts visible aircraft in configured bbox; cargo classification is a coarse MVP proxy.",
                "public_data_boundary": "Public ADS-B aggregation endpoint; no interception or private feed.",
            }
        except Exception as exc:  # noqa: BLE001
            return 0, {"error": str(exc), "bbox": asset.bbox, "provider": "OpenSky Network public states API"}


def _parse_wind_mph(text: str) -> float:
    parts = str(text).replace("to", " ").replace("mph", "").split()
    values = []
    for part in parts:
        try:
            values.append(float(part))
        except ValueError:
            continue
    return max(values) if values else 0.0
