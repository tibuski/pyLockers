"""Command-line tools for the Relaxx System API.

Usage:
    uv run python pylockertools.py <command> [options]

Available commands:
    exportusers    Export locker users to a CSV file
"""

import argparse
import csv
import sys
from pathlib import Path

from pylockers import RelaxxApiError, RelaxxClient

USER_FIELDS = [
    ("id", "Id"),
    ("first_name", "FirstName"),
    ("last_name", "LastName"),
    ("email", "Email"),
    ("member_number", "MemberNumber"),
    ("department", "Department"),
    ("remark", "Remark"),
    ("is_active", "IsActive"),
]


def cmd_exportusers(client: RelaxxClient, args: argparse.Namespace) -> int:
    """Export all locker users to a CSV file."""
    users = list(client.iter_locker_users(search_text=args.search))

    output = Path(args.output)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[header for _, header in USER_FIELDS])
        writer.writeheader()
        for user in users:
            writer.writerow(
                {header: getattr(user, attr) for attr, header in USER_FIELDS}
            )

    print(f"Exported {len(users)} user(s) to {output.resolve()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pylockertools",
        description="Tools for the Relaxx System API",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    export = subparsers.add_parser(
        "exportusers", help="Export locker users to a CSV file"
    )
    export.add_argument(
        "-o",
        "--output",
        default="locker_users.csv",
        help="Output CSV file (default: locker_users.csv)",
    )
    export.add_argument(
        "-s", "--search", default=None, help="Optional search text filter"
    )
    export.set_defaults(func=cmd_exportusers)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        with RelaxxClient.from_env() as client:
            return args.func(client, args)
    except RelaxxApiError as exc:
        print(f"API error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
