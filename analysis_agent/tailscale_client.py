from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

import httpx

from analysis_agent.config import get_settings


class TailscaleClientError(Exception):
    pass


OAUTH_TOKEN_URL = "https://api.tailscale.com/api/v2/oauth/token"
API_BASE = "https://api.tailscale.com/api/v2"
DEVICES_CACHE_TTL_SEC = 30
TOKEN_EXPIRY_SAFETY_MARGIN_SEC = 30


class TailscaleClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._devices_cache: list[dict[str, Any]] | None = None
        self._devices_cached_at: float = 0.0

    async def _get_token(self, force_refresh: bool = False) -> str:
        now = time.monotonic()
        if not force_refresh and self._token and now < self._token_expires_at - TOKEN_EXPIRY_SAFETY_MARGIN_SEC:
            return self._token

        if not self.settings.tailscale_oauth_client_id or not self.settings.tailscale_oauth_client_secret:
            raise TailscaleClientError("TAILSCALE_OAUTH_CLIENT_ID/TAILSCALE_OAUTH_CLIENT_SECRET not configured")

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                OAUTH_TOKEN_URL,
                data={
                    "client_id": self.settings.tailscale_oauth_client_id,
                    "client_secret": self.settings.tailscale_oauth_client_secret,
                },
            )
        if response.status_code != 200:
            raise TailscaleClientError(f"OAuth token request failed: {response.status_code} {response.text}")

        data = response.json()
        self._token = str(data["access_token"])
        self._token_expires_at = now + float(data.get("expires_in", 3600))
        return self._token

    async def list_devices(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        now = time.monotonic()
        if not force_refresh and self._devices_cache is not None and (now - self._devices_cached_at) < DEVICES_CACHE_TTL_SEC:
            return self._devices_cache

        token = await self._get_token()
        url = f"{API_BASE}/tailnet/{self.settings.tailscale_tailnet}/devices"

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {token}"})

        if response.status_code == 401:
            token = await self._get_token(force_refresh=True)
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers={"Authorization": f"Bearer {token}"})

        if response.status_code != 200:
            raise TailscaleClientError(f"Tailscale devices request failed: {response.status_code} {response.text}")

        devices = response.json().get("devices", [])
        self._devices_cache = devices
        self._devices_cached_at = now
        return devices


@lru_cache
def get_tailscale_client() -> TailscaleClient:
    return TailscaleClient()
