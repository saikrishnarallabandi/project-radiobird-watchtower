from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from .models import Anomaly, Asset


def build_market_notes(assets: list[Asset], anomalies: list[Anomaly]) -> list[str]:
    assets_by_id = {asset.id: asset for asset in assets}
    grouped: dict[str, list[Anomaly]] = defaultdict(list)
    for anomaly in anomalies:
        grouped[anomaly.asset_id].append(anomaly)

    notes: list[str] = []
    for asset_id, items in grouped.items():
        asset = assets_by_id[asset_id]
        top = max(items, key=lambda item: item.confidence)
        metrics = ", ".join(f"{item.metric}({item.severity})" for item in items)
        tickers = ", ".join(asset.tickers) if asset.tickers else "unmapped"
        next_check = datetime.now(timezone.utc) + timedelta(minutes=asset.cadence_minutes)
        next_check_text = next_check.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        notes.append(
            f"{asset.name}: {metrics}. Affected tickers/themes: {tickers}. "
            f"Confidence {top.confidence:.0%}. Next check: {next_check_text}. "
            "Verify provider data freshness and whether this persists."
        )
    return notes
