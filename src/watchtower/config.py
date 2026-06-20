from __future__ import annotations

import json
from pathlib import Path

from .models import Asset, MetricRule


def load_assets(path: str | Path) -> list[Asset]:
    raw = json.loads(Path(path).read_text())
    assets: list[Asset] = []
    for item in raw.get("assets", []):
        metrics = {
            name: MetricRule(baseline=float(rule["baseline"]), direction=rule.get("direction", "up"))
            for name, rule in item.get("metrics", {}).items()
        }
        assets.append(
            Asset(
                id=item["id"],
                name=item["name"],
                theme=item.get("theme", "unknown"),
                location=item["location"],
                tickers=list(item.get("tickers", [])),
                metrics=metrics,
                latitude=item.get("latitude"),
                longitude=item.get("longitude"),
                bbox=dict(item.get("bbox", {})),
                cadence_minutes=int(item.get("cadence_minutes", 60)),
                providers=dict(item.get("providers", {})),
            )
        )
    return assets
