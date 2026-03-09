"""Serviço para geocodificação automática via OpenRouteService."""

from __future__ import annotations

import os
from typing import Any

import requests

ORS_GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"


class GeocodeService:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("ORS_API_KEY", "")

    def geocode(self, endereco: str) -> tuple[float, float] | None:
        if not self.api_key:
            return None

        try:
            response = requests.get(
                ORS_GEOCODE_URL,
                headers={"Authorization": self.api_key},
                params={"text": endereco, "size": 1},
                timeout=15,
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            features = payload.get("features", [])
            if not features:
                return None
            lon, lat = features[0]["geometry"]["coordinates"]
            return lat, lon
        except requests.RequestException:
            return None
