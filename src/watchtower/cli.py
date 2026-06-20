from __future__ import annotations

import argparse

from .anomaly import score_observations
from .config import load_assets
from .ingestors import FixtureIngestor, WeatherIngestor
from .market import build_market_notes
from .storage import Store


def cmd_init_db(args: argparse.Namespace) -> None:
    Store(args.db).init()
    print(f"Initialized {args.db}")


def cmd_ingest(args: argparse.Namespace) -> None:
    assets = load_assets(args.config)
    store = Store(args.db)
    store.init()
    observations = []
    observations.extend(FixtureIngestor(args.fixtures).ingest(assets))
    if not args.no_weather:
        observations.extend(WeatherIngestor().ingest(assets))
    store.add_observations(observations)
    print(f"Stored {len(observations)} observations")


def cmd_score(args: argparse.Namespace) -> None:
    assets = load_assets(args.config)
    store = Store(args.db)
    anomalies = score_observations(assets, store.latest_observations())
    store.replace_anomalies(anomalies)
    print(f"Scored {len(anomalies)} anomalies")


def cmd_report(args: argparse.Namespace) -> None:
    assets = load_assets(args.config)
    anomalies = Store(args.db).all_anomalies()
    if not anomalies:
        print("Supply Chain Watchtower: no active anomalies.")
        return
    print("Supply Chain Watchtower anomalies:")
    for note in build_market_notes(assets, anomalies):
        print(f"- {note}")


def cmd_run(args: argparse.Namespace) -> None:
    cmd_ingest(args)
    cmd_score(args)
    cmd_report(args)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="watchtower")
    p.add_argument("--db", default="watchtower.db")
    sub = p.add_subparsers(dest="cmd", required=True)

    init_db = sub.add_parser("init-db")
    init_db.set_defaults(func=cmd_init_db)

    for name, func in [
        ("ingest", cmd_ingest),
        ("score", cmd_score),
        ("report", cmd_report),
        ("run", cmd_run),
    ]:
        child = sub.add_parser(name)
        child.add_argument("--config", default="config/watchlist.example.json")
        child.add_argument("--fixtures", default="data/fixtures/supply_events.json")
        child.add_argument("--no-weather", action="store_true")
        child.set_defaults(func=func)
    return p


def main() -> None:
    args = parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
