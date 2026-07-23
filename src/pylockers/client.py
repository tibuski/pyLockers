"""Typed HTTP client for the Relaxx System API.

Usage:
    from pylockers import RelaxxClient

    with RelaxxClient.from_env() as client:
        lockers = client.get_lockers()
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Self
from uuid import UUID

import httpx

from pylockers.config import Settings, get_settings
from pylockers.models import (
    Locker,
    LockerAction,
    LockerUser,
    LockerUserDetail,
    PagedResult,
)


class RelaxxApiError(Exception):
    """Raised when the API returns an error response."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")


class RelaxxClient:
    """Synchronous client for the Relaxx System API.

    Handles authentication (X-API-KEY header), timeouts and retries.
    Prefer using it as a context manager so connections are closed properly.
    """

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 10.0) -> None:
        if not api_key:
            msg = "An API key is required (set RELAXX_API_KEY)."
            raise ValueError(msg)
        transport = httpx.HTTPTransport(retries=3)
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"X-API-KEY": api_key, "Accept": "application/json"},
            timeout=httpx.Timeout(timeout),
            transport=transport,
        )

    @classmethod
    def from_env(cls, settings: Settings | None = None) -> Self:
        """Build a client from environment variables / .env file."""
        settings = settings or get_settings()
        return cls(
            base_url=settings.base_url,
            api_key=settings.api_key.get_secret_value(),
            timeout=settings.timeout,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    # -- low-level ------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = self._http.request(method, path, **kwargs)
        if response.is_error:
            raise RelaxxApiError(response.status_code, response.text)
        return response

    # -- lockers ---------------------------------------------------------

    def get_lockers(
        self,
        *,
        search_text: str | None = None,
        rented: bool | None = None,
        blocked: bool | None = None,
        page_number: int = 1,
        page_size: int = 50,
    ) -> PagedResult[Locker]:
        """Get a filtered, paginated list of lockers."""
        params: dict[str, Any] = {"PageNumber": page_number, "PageSize": page_size}
        if search_text is not None:
            params["SearchText"] = search_text
        if rented is not None:
            params["Rented"] = rented
        if blocked is not None:
            params["Blocked"] = blocked
        response = self._request("GET", "/lockers", params=params)
        return PagedResult[Locker].model_validate(response.json())

    def get_locker(self, locker_id: UUID) -> Locker:
        """Get a single locker by its Id."""
        response = self._request("GET", f"/lockers/{locker_id}")
        return Locker.model_validate(response.json())

    def execute_locker_action(self, locker_id: UUID, action: LockerAction) -> None:
        """Execute an action (e.g. open) on a locker."""
        self._request(
            "POST",
            f"/lockers/{locker_id}/action",
            json={"action": str(action)},
        )

    # -- locker users -----------------------------------------------------

    def get_locker_users(
        self,
        *,
        search_text: str | None = None,
        page_number: int = 1,
        page_size: int = 50,
    ) -> PagedResult[LockerUser]:
        """Get a filtered, paginated list of locker users."""
        params: dict[str, Any] = {"PageNumber": page_number, "PageSize": page_size}
        if search_text is not None:
            params["SearchText"] = search_text
        response = self._request("GET", "/locker-users", params=params)
        return PagedResult[LockerUser].model_validate(response.json())

    def get_locker_user(self, locker_user_id: UUID) -> LockerUserDetail:
        """Get full details of a locker user (groups, data carriers, lockers)."""
        response = self._request("GET", f"/locker-users/{locker_user_id}")
        return LockerUserDetail.model_validate(response.json())

    def iter_locker_users(
        self, *, search_text: str | None = None, page_size: int = 100
    ) -> Iterator[LockerUser]:
        """Yield all locker users, transparently following pagination."""
        page_number = 1
        while True:
            page = self.get_locker_users(
                search_text=search_text, page_number=page_number, page_size=page_size
            )
            yield from page.results
            if page_number * page_size >= page.total_records or not page.results:
                return
            page_number += 1
