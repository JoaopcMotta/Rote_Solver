"""OpenRouteService API client with geocoding and matrix batch support."""

from __future__ import annotations

import os
from typing import Any

import requests


class OpenRouteServiceClient:
    BASE = "https://api.openrouteservice.org"

    def __init__(self, api_key: str | None = None, timeout: int = 30) -> None:
        self.api_key = api_key or os.getenv("ORS_API_KEY", "")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def geocode(self, address: str) -> tuple[float, float] | None:
        """Return (lat, lon) for an address, or None if unavailable."""
        if not self.enabled:
            return None

        resp = requests.get(
            f"{self.BASE}/geocode/search",
            headers={"Authorization": self.api_key},
            params={"text": address, "size": 1},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        features = payload.get("features", [])
        if not features:
            return None

        lon, lat = features[0]["geometry"]["coordinates"]
        return float(lat), float(lon)

    def matrix(
        self,
        coordinates: list[tuple[float, float]],
        sources: list[int],
        destinations: list[int],
        profile: str = "driving-car",
    ) -> dict[str, Any]:
        """Call ORS matrix endpoint for multiple sources/destinations in one request."""
        if not self.enabled:
            raise RuntimeError("ORS_API_KEY não configurada para consulta online.")

        body = {
            "locations": [[lon, lat] for lat, lon in coordinates],
            "sources": sources,
            "destinations": destinations,
            "metrics": ["distance", "duration"],
        }
        resp = requests.post(
            f"{self.BASE}/v2/matrix/{profile}",
            headers={"Authorization": self.api_key, "Content-Type": "application/json"},
            json=body,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()
