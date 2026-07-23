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

| Command       | Description                                            |
| ------------- | ------------------------------------------------------ |
| `exportusers` | Export locker users to a CSV file (import format)      |
| `importusers` | Import locker users (and cards) from a CSV file        |

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
