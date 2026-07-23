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


USER_CSV_FIELDS = (
    "firstName",
    "lastName",
    "email",
    "memberNumber",
    "department",
    "remark",
    "authorizationGroupId",
)


def _parse_bool(value: str | None, *, default: bool = True) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("true", "1", "yes")


def _err_msg(error: dict | None) -> str:
    """Extract a readable message from an API error object."""
    if isinstance(error, dict):
        return str(error.get("message") or error)
    return str(error)


def cmd_importusers(client: RelaxxClient, args: argparse.Namespace) -> int:
    """Import locker users (and their data carriers) from a CSV file.

    Existing users are matched by memberNumber, then email, then name,
    and updated in place; unmatched rows create new users. Data carriers
    are matched by cardUID per user.
    """
    with Path(args.input).open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("No rows found in input file.", file=sys.stderr)
        return 1

    existing = list(client.iter_locker_users())
    by_member = {u.member_number: u for u in existing if u.member_number}
    by_email = {u.email.lower(): u for u in existing if u.email}
    by_name = {
        (u.first_name or "").lower() + " " + (u.last_name or "").lower(): u
        for u in existing
    }

    def match_user(row: dict[str, str]):
        if user := by_member.get(row.get("memberNumber") or ""):
            return user
        if user := by_email.get((row.get("email") or "").lower()):
            return user
        first, last = row.get("firstName") or "", row.get("lastName") or ""
        return by_name.get(f"{first} {last}".strip().lower())

    user_payloads = []
    for row in rows:
        payload = {k: row[k] for k in USER_CSV_FIELDS if row.get(k)}
        payload["isActive"] = _parse_bool(row.get("isActive"))
        if match := match_user(row):
            payload["id"] = str(match.id)
        user_payloads.append(payload)

    n_update = sum(1 for p in user_payloads if "id" in p)
    print(f"{len(rows)} row(s): {n_update} update(s), {len(rows) - n_update} create(s)")
    if args.dry_run:
        for row, payload in zip(rows, user_payloads, strict=True):
            action = "UPDATE" if "id" in payload else "CREATE"
            card = f" + card {row['cardUID']}" if row.get("cardUID") else ""
            print(f"  {action}: {row.get('firstName')} {row.get('lastName')}{card}")
        return 0

    results = client.bulk_upsert_locker_users(user_payloads)
    # The bulk-upsert response is positional: resolve the user id per row,
    # falling back to the id of a matched existing user.
    row_user_ids: list[str | None] = []
    failures = 0
    for row, payload, result in zip(rows, user_payloads, results, strict=True):
        if result.success and result.data and result.data.get("id"):
            row_user_ids.append(result.data["id"])
        elif result.success and payload.get("id"):
            row_user_ids.append(payload["id"])
        else:
            row_user_ids.append(None)
            failures += 1
            name = f"{row.get('firstName')} {row.get('lastName')}".strip()
            print(
                f"  FAILED user {name or row.get('memberNumber')}: "
                f"{_err_msg(result.error)}",
                file=sys.stderr,
            )

    # Data carriers: match by cardUID per user so re-imports update.
    carrier_payloads = []
    detail_cache = {}
    for row, user_id in zip(rows, row_user_ids, strict=True):
        if not row.get("cardUID"):
            continue
        if not row.get("dataCarrierTypeId"):
            print(
                f"  SKIP card {row['cardUID']}: missing dataCarrierTypeId",
                file=sys.stderr,
            )
            continue
        if not user_id:
            name = f"{row.get('firstName')} {row.get('lastName')}"
            print(
                f"  SKIP card {row['cardUID']}: user {name} not imported",
                file=sys.stderr,
            )
            continue
        if user_id not in detail_cache:
            detail_cache[user_id] = {
                dc.card_uid: dc
                for dc in client.get_locker_user(user_id).data_carriers
                if dc.card_uid
            }
        carrier = {
            "dataCarrierTypeId": row["dataCarrierTypeId"],
            "lockerUserId": user_id,
            "cardUID": row["cardUID"],
            "isActive": True,
        }
        if row.get("friendlyName"):
            carrier["friendlyName"] = row["friendlyName"]
        if row.get("validFrom"):
            carrier["validFrom"] = row["validFrom"]
        if row.get("validUntil"):
            carrier["validUntil"] = row["validUntil"]
        if existing_card := detail_cache[user_id].get(row["cardUID"]):
            carrier["id"] = str(existing_card.id)
        carrier_payloads.append(carrier)

    if carrier_payloads:
        results = client.bulk_upsert_data_carriers(carrier_payloads)
        for carrier, result in zip(carrier_payloads, results, strict=True):
            if not result.success:
                failures += 1
                print(
                    f"  FAILED card {carrier['cardUID']}: "
                    f"{_err_msg(result.error)}",
                    file=sys.stderr,
                )

    print(
        f"Imported {len(user_payloads)} user(s), {len(carrier_payloads)} card(s), "
        f"{failures} failure(s)"
    )
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pylockertools",
        description="Tools for the Relaxx System API (locker management).",
        epilog="""\
examples:
  %(prog)s exportusers                          Export all users to locker_users.csv
  %(prog)s exportusers -o users.csv -s "tran"   Export filtered users to a file
  %(prog)s importusers users.csv --dry-run      Preview an import (no changes)
  %(prog)s importusers users.csv                Import users and cards from CSV

typical workflow:
  1. exportusers                 -> get a CSV of current users
  2. edit the CSV                -> add/change rows
  3. importusers ... --dry-run   -> check what would be created vs updated
  4. importusers ...             -> apply

configuration:
  API connection is read from .env or environment variables:
  RELAXX_BASE_URL, RELAXX_API_KEY, RELAXX_TIMEOUT (see .env.example)

Run '%(prog)s <command> -h' for command-specific options.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", title="commands")

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

    imp = subparsers.add_parser(
        "importusers", help="Import locker users (and cards) from a CSV file"
    )
    imp.add_argument("input", help="Input CSV file (user import format)")
    imp.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created/updated without writing",
    )
    imp.set_defaults(func=cmd_importusers)

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
