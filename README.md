# pyLockers

Python client for the **Relaxx System API** (see `relaxx-systemapi-revised-09-07-2026.json`).

## Setup

```bash
uv sync
cp .env.example .env   # then fill in your API key
```

Configuration is read from environment variables (prefix `RELAXX_`) or `.env`:

| Variable           | Default                 | Description          |
| ------------------ | ----------------------- | -------------------- |
| `RELAXX_BASE_URL`  | `http://localhost:5000` | API base URL         |
| `RELAXX_API_KEY`   | *(required)*            | `X-API-KEY` header   |
| `RELAXX_TIMEOUT`   | `10.0`                  | HTTP timeout (secs)  |

## Usage

```bash
uv run python -m pylockers
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

## Development

```bash
uv run ruff check .   # lint
uv run ruff format .  # format
```
