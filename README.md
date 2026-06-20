# RadioBird Supply Chain Watchtower

Public-data supply-chain anomaly monitor built from the RadioBird direction.

The system watches supply-chain regions/assets using legal public data only,
scores deviations from local baselines, and emits market-facing notes.

## MVP Scope

- Config-driven watchlist of regions/assets and linked tickers.
- SQLite event/baseline/anomaly store.
- Public-data ingestor interface.
- Fixture ingestor for AIS/ADS-B style activity until provider keys are added.
- Weather ingestor using wttr.in JSON for live environmental disruption context.
- NOAA/NWS public weather adapter for US assets with coordinates.
- OpenSky public ADS-B adapter for anonymous bbox aircraft counts.
- Simple baseline anomaly scoring.
- CLI reports suitable for group discussion.

## Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
watchtower init-db
watchtower ingest --config config/watchlist.example.json
watchtower score --config config/watchlist.example.json
watchtower report --config config/watchlist.example.json
```

Or run the full pipeline:

```bash
watchtower run --config config/watchlist.example.json
```

Run with public provider adapters:

```bash
watchtower run --config config/watchlist.example.json --weather-provider noaa --adsb-provider opensky
```

The NOAA adapter only emits observations for US assets with coordinates. The OpenSky adapter counts visible aircraft in each asset bbox as a coarse MVP proxy.

## Cadence Runner

Run only assets due for their configured cadence:

```bash
watchtower cadence --config config/watchlist.example.json --state data/cadence_state.json
```

Force an immediate hourly-style sweep:

```bash
watchtower cadence --config config/watchlist.example.json --force
```

Cron example:

```cron
0 * * * * cd /home2/srallaba/projects/project_radiobird_watchtower && . .venv/bin/activate && watchtower cadence --config config/watchlist.example.json >> data/watchtower.log 2>&1
```

## Legal Boundary

This project is for public/legal data sources only: public weather, AIS/ADS-B
providers, satellite pass metadata, public imagery metadata, and owned/authorized
RF captures. It must not decode secret communications or bypass access controls.
