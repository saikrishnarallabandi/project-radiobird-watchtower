#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = "saikrishnarallabandi/project-radiobird-watchtower"
DEFAULT_ISSUE = "6"
PRIVACY_GUARD_ENV = "WATCHTOWER_PRIVACY_GUARD"


def run(cmd: list[str], *, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        input=input_text,
        text=True,
        capture_output=True,
        check=check,
    )


def truncate(text: str, limit: int = 3500) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n...[truncated]"


def clean_for_github(message: str) -> str:
    guard_path = os.environ.get(PRIVACY_GUARD_ENV)
    if not guard_path:
        raise RuntimeError(f"{PRIVACY_GUARD_ENV} must point to a local privacy guard before posting to GitHub")
    privacy_guard = Path(guard_path).expanduser()
    if not privacy_guard.exists():
        raise FileNotFoundError(f"privacy guard missing at configured path: {PRIVACY_GUARD_ENV}")
    result = run([sys.executable, str(privacy_guard), "--surface", "github"], input_text=message)
    cleaned = result.stdout.strip()
    return cleaned or message


def build_comment(command_output: str, exit_code: int, *, forced: bool) -> str:
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    status = "completed" if exit_code == 0 else f"failed with exit code {exit_code}"
    mode = "forced cadence sweep" if forced else "scheduled cadence sweep"
    return (
        f"Hourly Watchtower checkpoint ({stamp})\n\n"
        f"- Mode: {mode}\n"
        f"- Status: {status}\n"
        "- Boundary: public/legal data only; no secret comms, interception, or non-public feeds.\n\n"
        "```text\n"
        f"{truncate(command_output.strip() or '(no output)')}\n"
        "```"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RadioBird Watchtower cadence and post a GitHub issue checkpoint.")
    parser.add_argument("--repo", default=os.environ.get("WATCHTOWER_GITHUB_REPO", DEFAULT_REPO))
    parser.add_argument("--issue", default=os.environ.get("WATCHTOWER_GITHUB_ISSUE", DEFAULT_ISSUE))
    parser.add_argument("--config", default="config/watchlist.example.json")
    parser.add_argument("--db", default="data/watchtower.db")
    parser.add_argument("--state", default="data/cadence_state.json")
    parser.add_argument("--weather-provider", choices=["wttr", "noaa"], default="noaa")
    parser.add_argument("--adsb-provider", choices=["none", "opensky"], default="opensky")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-comment", action="store_true")
    args = parser.parse_args()

    cmd = [
        sys.executable,
        "-m",
        "watchtower.cli",
        "--db",
        args.db,
        "cadence",
        "--config",
        args.config,
        "--state",
        args.state,
        "--weather-provider",
        args.weather_provider,
        "--adsb-provider",
        args.adsb_provider,
    ]
    if args.force:
        cmd.append("--force")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, env=env)
    output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part)

    if not args.no_comment:
        comment = clean_for_github(build_comment(output, result.returncode, forced=args.force))
        run(["gh", "issue", "comment", args.issue, "--repo", args.repo, "--body", comment])

    print(output)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

