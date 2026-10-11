import argparse
import logging
from pathlib import Path

import httpx

from ticket_cleaner.config import Settings, load_settings
from ticket_cleaner.files import read_rows, write_json
from ticket_cleaner.parsing import split_records
from ticket_cleaner.records import STATUSES
from ticket_cleaner.remote import fetch_rows
from ticket_cleaner.report import build_summary

logger = logging.getLogger("ticket_cleaner")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ticket_cleaner",
        description="Check support-ticket records and write a summary report.",
    )
    parser.add_argument(
        "input", help="a .csv or .json file of tickets, or 'remote' to download them"
    )
    parser.add_argument(
        "--status",
        default="open",
        choices=sorted(STATUSES),
        help="which tickets to count (default: open)",
    )
    parser.add_argument(
        "--category",
        action="append",
        metavar="NAME",
        help="count only this category; give it again for more categories",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/summary.json"),
        help="where to save the report (default: reports/summary.json)",
    )
    return parser


def load_rows(source: str, settings: Settings) -> list[dict]:
    """Return raw records from a file, or from the web service for "remote"."""
    if source == "remote":
        return fetch_rows(settings.tickets_url, token=settings.api_token)
    return read_rows(Path(source))


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    settings = load_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(levelname)s %(name)s: %(message)s"
    )
    logger.info("reading tickets from %s", args.input)

    try:
        rows = load_rows(args.input, settings)
    except (OSError, ValueError, httpx.HTTPError) as error:
        logger.error("cannot read the tickets from %s: %s", args.input, error)
        return 1

    tickets, rejected = split_records(rows)
    for record in rejected:
        logger.warning("row %d rejected: %s", record.row, "; ".join(record.problems))

    summary = build_summary(tickets, rejected, args.status, args.category)
    write_json(summary, args.output)
    logger.info("wrote %s", args.output)
    print(f"{len(rows)} rows: {len(tickets)} valid, {len(rejected)} rejected.")
    print(f"Report: {args.output}")
    return 0
