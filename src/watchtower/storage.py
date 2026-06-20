from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import Anomaly, Observation


SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id TEXT NOT NULL,
  source TEXT NOT NULL,
  metric TEXT NOT NULL,
  value REAL NOT NULL,
  unit TEXT,
  observed_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS anomalies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id TEXT NOT NULL,
  source TEXT NOT NULL,
  metric TEXT NOT NULL,
  value REAL NOT NULL,
  baseline REAL NOT NULL,
  severity TEXT NOT NULL,
  confidence REAL NOT NULL,
  reason TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: str | Path = "watchtower.db") -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        if self.path != Path(":memory:"):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def init(self) -> None:
        with self.connect() as con:
            con.executescript(SCHEMA)

    def add_observations(self, observations: list[Observation]) -> None:
        with self.connect() as con:
            con.executemany(
                """
                INSERT INTO observations
                  (asset_id, source, metric, value, unit, observed_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        obs.asset_id,
                        obs.source,
                        obs.metric,
                        obs.value,
                        obs.unit,
                        obs.observed_at,
                        json.dumps(obs.metadata, sort_keys=True),
                    )
                    for obs in observations
                ],
            )

    def latest_observations(self) -> list[Observation]:
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT o.* FROM observations o
                JOIN (
                  SELECT asset_id, source, metric, MAX(id) AS id
                  FROM observations
                  GROUP BY asset_id, source, metric
                ) latest
                ON latest.id = o.id
                ORDER BY o.asset_id, o.metric
                """
            ).fetchall()
        return [
            Observation(
                asset_id=row["asset_id"],
                source=row["source"],
                metric=row["metric"],
                value=float(row["value"]),
                unit=row["unit"] or "",
                observed_at=row["observed_at"],
                metadata=json.loads(row["metadata_json"]),
            )
            for row in rows
        ]

    def replace_anomalies(self, anomalies: list[Anomaly]) -> None:
        with self.connect() as con:
            con.execute("DELETE FROM anomalies")
            con.executemany(
                """
                INSERT INTO anomalies
                  (asset_id, source, metric, value, baseline, severity, confidence, reason, observed_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.asset_id,
                        item.source,
                        item.metric,
                        item.value,
                        item.baseline,
                        item.severity,
                        item.confidence,
                        item.reason,
                        item.observed_at,
                        item.created_at,
                    )
                    for item in anomalies
                ],
            )

    def all_anomalies(self) -> list[Anomaly]:
        with self.connect() as con:
            rows = con.execute("SELECT * FROM anomalies ORDER BY confidence DESC, asset_id").fetchall()
        return [
            Anomaly(
                asset_id=row["asset_id"],
                source=row["source"],
                metric=row["metric"],
                value=float(row["value"]),
                baseline=float(row["baseline"]),
                severity=row["severity"],
                confidence=float(row["confidence"]),
                reason=row["reason"],
                observed_at=row["observed_at"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
