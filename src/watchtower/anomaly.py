from __future__ import annotations

from .models import Anomaly, Asset, Observation


def score_observations(assets: list[Asset], observations: list[Observation]) -> list[Anomaly]:
    assets_by_id = {asset.id: asset for asset in assets}
    anomalies: list[Anomaly] = []
    for obs in observations:
        asset = assets_by_id.get(obs.asset_id)
        if not asset:
            continue
        rule = asset.metrics.get(obs.metric)
        if not rule:
            continue
        baseline = rule.baseline
        if baseline == 0:
            delta_ratio = obs.value
        elif rule.direction == "down":
            delta_ratio = (baseline - obs.value) / baseline
        else:
            delta_ratio = (obs.value - baseline) / baseline

        if delta_ratio < 0.20:
            continue
        severity = "high" if delta_ratio >= 0.50 else "medium" if delta_ratio >= 0.30 else "low"
        confidence = min(0.95, 0.45 + max(0.0, delta_ratio))
        direction_text = "below" if rule.direction == "down" else "above"
        reason = f"{obs.metric} is {delta_ratio:.0%} {direction_text} baseline ({obs.value:g} vs {baseline:g})"
        anomalies.append(
            Anomaly(
                asset_id=obs.asset_id,
                source=obs.source,
                metric=obs.metric,
                value=obs.value,
                baseline=baseline,
                severity=severity,
                confidence=round(confidence, 2),
                reason=reason,
                observed_at=obs.observed_at,
            )
        )
    return anomalies
