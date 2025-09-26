import os
from datetime import datetime, timedelta
import yaml
from rich import print

from .orchestrate_day import orchestrate as orchestrate_day


def load_params() -> dict:
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "params.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def orchestrate_range(end_date_iso: str, days: int) -> None:
    end_date = datetime.fromisoformat(end_date_iso)
    start_date = end_date - timedelta(days=days - 1)
    print(f"[bold cyan]Running range {start_date.date()}..{end_date.date()}[/bold cyan]")
    for i in range(days):
        d = start_date + timedelta(days=i)
        orchestrate_day(d.date().isoformat())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run N-day dust pipeline range")
    parser.add_argument("--end", required=False, help="End date ISO, default today UTC")
    parser.add_argument("--days", required=False, type=int, default=3, help="Number of days")
    args = parser.parse_args()

    end_iso = args.end or datetime.utcnow().date().isoformat()
    orchestrate_range(end_iso, args.days)


