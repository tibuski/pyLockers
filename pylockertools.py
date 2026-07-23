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

# Columns match the user import format, so exports can be re-imported.
EXPORT_FIELDS = [
    "firstName",
    "lastName",
    "email",
    "memberNumber",
    "department",
    "remark",
    "isActive",
    "authorizationGroupId",
    "cardUID",
    "friendlyName",
    "dataCarrierTypeId",
    "validFrom",
    "validUntil",
]


def _bool(value: bool) -> str:
    return "true" if value else "false"


def _dt(value: object) -> str:
    return value.isoformat() if value is not None else ""


def cmd_exportusers(client: RelaxxClient, args: argparse.Namespace) -> int:
    """Export all locker users to a CSV file in the user import format.

    Emits one row per data carrier; users without a data carrier get a
    single row with empty card columns.
    """
    rows = []
    users = list(client.iter_locker_users(search_text=args.search))
    for user in users:
        detail = client.get_locker_user(user.id)
        base = {
            "firstName": detail.first_name or "",
            "lastName": detail.last_name or "",
            "email": detail.email or "",
            "memberNumber": detail.member_number or "",
            "department": detail.department or "",
            "remark": detail.remark or "",
            "isActive": _bool(detail.is_active),
            "authorizationGroupId": (
                str(detail.authorization_group.id)
                if detail.authorization_group and detail.authorization_group.id
                else ""
            ),
        }
        carriers = detail.data_carriers or [None]
        for carrier in carriers:
            carrier_type = carrier.data_carrier_type if carrier else None
            rows.append(
                base
                | {
                    "cardUID": carrier.card_uid or "" if carrier else "",
                    # friendlyName: the detail DTO has no per-carrier name,
                    # so we export the data carrier type name.
                    "friendlyName": carrier_type.name or "" if carrier_type else "",
                    "dataCarrierTypeId": str(carrier_type.id) if carrier_type else "",
                    "validFrom": _dt(carrier.valid_from) if carrier else "",
                    "validUntil": _dt(carrier.valid_until) if carrier else "",
                }
            )

    output = Path(args.output)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {len(users)} user(s), {len(rows)} row(s) to {output.resolve()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pylockertools",
        description="Tools for the Relaxx System API",
    )
    subparsers = parser.add_subparsers(dest="command")

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
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "func", None):
        # No command given: show help instead of an error.
        parser.print_help()
        return 0
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
