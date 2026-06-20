from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Asset


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def load_state(path: str | Path) -> dict[str, str]:
    state_path = Path(path)
    if not state_path.exists():
        return {}
    return json.loads(state_path.read_text())


def save_state(path: str | Path, state: dict[str, str]) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def due_assets(
    assets: list[Asset],
    state: dict[str, str],
    *,
    now: datetime | None = None,
    force: bool = False,
    grace_minutes: float = 2.0,
) -> list[Asset]:
    if force:
        return assets
    now = now or utc_now()
    due: list[Asset] = []
    for asset in assets:
        last_raw = state.get(asset.id)
        if not last_raw:
            due.append(asset)
            continue
        last = datetime.fromisoformat(last_raw.replace("Z", "+00:00"))
        elapsed_minutes = (now - last).total_seconds() / 60
        if elapsed_minutes + grace_minutes >= asset.cadence_minutes:
            due.append(asset)
    return due


def mark_checked(assets: list[Asset], state: dict[str, str], *, now: datetime | None = None) -> dict[str, str]:
    stamp = (now or utc_now()).isoformat().replace("+00:00", "Z")
    for asset in assets:
        state[asset.id] = stamp
    return state
