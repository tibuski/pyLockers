"""Demo: connect to the Relaxx System API on localhost and list lockers.

Run with: uv run python -m pylockers
"""

import httpx

from pylockers import RelaxxApiError, RelaxxClient
from pylockers.config import get_settings


def main() -> None:
    settings = get_settings()
    print(f"Connecting to Relaxx System API at {settings.base_url} ...")

    try:
        with RelaxxClient.from_env(settings) as client:
            page = client.get_lockers(page_size=10)
            print(f"Found {page.total_records} locker(s):\n")
            for locker in page.results:
                print(
                    f"  #{locker.number or '?':<6} {locker.id}  "
                    f"door={locker.door_state}  connection={locker.connection_state}"
                )
    except httpx.ConnectError:
        print(f"Could not connect to {settings.base_url} — is the API running?")
        raise SystemExit(1) from None
    except RelaxxApiError as exc:
        print(f"The API returned an error: {exc}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
