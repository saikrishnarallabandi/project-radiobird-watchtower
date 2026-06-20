from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from watchtower.cadence import due_assets, mark_checked
from watchtower.config import load_assets
from watchtower.ingestors import FixtureIngestor, NoaaWeatherIngestor, OpenSkyAdsbIngestor
from watchtower.storage import Store


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse(self.payloads.pop(0))


class WatchtowerTests(unittest.TestCase):
    def test_fixture_roundtrip_scores(self):
        assets = load_assets("config/watchlist.example.json")
        observations = FixtureIngestor("data/fixtures/supply_events.json").ingest(assets)
        self.assertEqual(len(observations), 3)
        self.assertTrue(observations[0].metadata["fixture"])

        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "watchtower.db")
            store.init()
            store.add_observations(observations)
            store.add_observations(observations)
            latest = store.latest_observations()
            self.assertEqual(len(latest), 3)

    def test_noaa_weather_adapter_maps_public_forecast_to_risk(self):
        assets = load_assets("config/watchlist.example.json")
        houston = [asset for asset in assets if asset.id == "us_gulf_lng"]
        session = FakeSession(
            [
                {"properties": {"forecastHourly": "https://api.weather.gov/gridpoints/demo"}},
                {"properties": {"periods": [{"shortForecast": "Thunderstorms", "windSpeed": "20 to 45 mph", "temperature": 82}]}},
            ]
        )
        observations = NoaaWeatherIngestor(session=session).ingest(houston)
        self.assertEqual(observations[0].source, "weather_noaa")
        self.assertGreaterEqual(observations[0].value, 2.0)
        self.assertIn("Public NOAA", observations[0].metadata["public_data_boundary"])

    def test_opensky_adapter_counts_bbox_aircraft(self):
        assets = load_assets("config/watchlist.example.json")
        taiwan = [asset for asset in assets if asset.id == "taiwan_semis_ports"]
        session = FakeSession([{"states": [["a"], ["b"], ["c"]]}])
        observations = OpenSkyAdsbIngestor(session=session).ingest(taiwan)
        self.assertEqual(observations[0].source, "adsb_opensky")
        self.assertEqual(observations[0].value, 3)

    def test_cadence_due_assets(self):
        assets = load_assets("config/watchlist.example.json")
        now = datetime(2026, 6, 20, tzinfo=timezone.utc)
        state = {assets[0].id: (now - timedelta(minutes=30)).isoformat().replace("+00:00", "Z")}
        due = due_assets(assets, state, now=now)
        self.assertNotIn(assets[0], due)
        self.assertIn(assets[1], due)

        almost_due = {assets[0].id: (now - timedelta(minutes=59)).isoformat().replace("+00:00", "Z")}
        self.assertIn(assets[0], due_assets([assets[0]], almost_due, now=now))

        updated = mark_checked(due, state, now=now)
        self.assertEqual(updated[assets[1].id], "2026-06-20T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
