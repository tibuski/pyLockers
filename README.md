# pyLockers

Python client and CLI tools for the **Relaxx System API**
(see `relaxx-systemapi-revised-09-07-2026.json`).

## Setup

```bash
uv sync
cp .env.example .env   # then fill in your API key
```

Configuration is read from environment variables (prefix `RELAXX_`) or `.env`:

| Variable          | Default                 | Description         |
| ----------------- | ----------------------- | ------------------- |
| `RELAXX_BASE_URL` | `http://localhost:5000` | API base URL        |
| `RELAXX_API_KEY`  | *(required)*            | `X-API-KEY` header  |
| `RELAXX_TIMEOUT`  | `10.0`                  | HTTP timeout (secs) |

### Running from WSL2

The API typically runs on the Windows host. With WSL2 *mirrored* networking
(`networkingMode=mirrored` in `.wslconfig`), `http://localhost:<port>` works
directly. Otherwise use `http://<windows-hostname>.local:<port>` and make sure
the service binds to all interfaces and the firewall allows it. On a default
Gantner setup the System API listens on port **8243** (8241 is the web UI).

## CLI: pylockertools

```bash
uv run python pylockertools.py --help
```

| Command         | Description                                       |
| --------------- | ------------------------------------------------- |
| `exportusers`   | Export locker users to a CSV file (import format) |
| `importusers`   | Import locker users (and cards) from a CSV file   |
| `exportlockers` | Export all lockers to a CSV file                  |

### exportusers

```bash
uv run python pylockertools.py exportusers               # → locker_users.csv
uv run python pylockertools.py exportusers -o users.csv  # custom output file
uv run python pylockertools.py exportusers -s "tran"     # search filter
```

The CSV uses the user import format (one row per data carrier), so exports
can be edited and re-imported directly.

### importusers

```bash
uv run python pylockertools.py importusers users.csv --dry-run   # preview
uv run python pylockertools.py importusers users.csv             # apply
```

Existing users are matched by `memberNumber`, then `email`, then name, and
**updated in place**; unmatched rows create new users. Data carriers are
matched by `cardUID` per user. (The API's bulk-upsert creates duplicates
when no `id` is given — the tool resolves ids for you.)

Rows are validated before calling the API (`SKIP ...` with a reason) and
per-item API rejections are reported with the affected item and the API's
message, e.g. `FAILED card 2198065733: Data carrier is not unique.`
Note the bulk API returns HTTP 200 even for rejected items, so always
check the output. The exit code is `1` if any row failed.

### exportlockers

```bash
uv run python pylockertools.py exportlockers                # → lockers.csv
uv run python pylockertools.py exportlockers -o out.csv     # custom output file
uv run python pylockertools.py exportlockers -s "yellow"    # search filter
```

Exports every locker field the System API exposes: id, number, hardware
number, type, mode, door/connection state, flags (enabled, rented, blocked,
maintenance, alarmed), device and locker group, location, BLE metadata and
active alarms/warnings (joined with `;`).

Note: the System API is read-only for lockers apart from mode/actions, and
the display name shown in the Relaxx Web UI is stored in the web backend
(port 8241), not in the System API — so it is not part of this export.

### Large imports/exports

Bulk calls are chunked (500 items per request) with progress output, and
card matching skips users created during the import itself. Expect a few
minutes for thousands of users with cards (one detail request per existing
user is required by the API). Increase `RELAXX_TIMEOUT` if the API is slow.

## Library usage

```bash
uv run python -m pylockers   # demo: list lockers
```

Or in your own code:

```python
from pylockers import LockerAction, RelaxxClient

with RelaxxClient.from_env() as client:
    page = client.get_lockers(rented=False)
    for locker in page.results:
        print(locker.number, locker.door_state)

    # Open a locker:
    # client.execute_locker_action(locker.id, LockerAction.OPEN_LOCKER)
```

Available client methods: `get_lockers`, `get_locker`,
`execute_locker_action`, `get_locker_users`, `get_locker_user`,
`iter_locker_users`, `bulk_upsert_locker_users`,
`bulk_upsert_data_carriers`.

## Development

```bash
uv run ruff check .   # lint
uv run ruff format .  # format
```

Secrets live only in `.env`, which is gitignored — never commit it.
Exported CSV files (`*.csv`) are gitignored too, as they contain personal
data.
