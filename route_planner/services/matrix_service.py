"""Serviço de matriz de distâncias com cache em SQLite."""

from __future__ import annotations

import datetime as dt
import os
from typing import Any

import requests

from route_planner.database_manager import DatabaseManager

ORS_MATRIX_URL = "https://api.openrouteservice.org/v2/matrix/driving-car"


class MatrixService:
    def __init__(self, db: DatabaseManager, api_key: str | None = None) -> None:
        self.db = db
        self.api_key = api_key or os.getenv("ORS_API_KEY", "")

    def get_distance_time(
        self,
        origem_id: str,
        destino_id: str,
        origem_coord: tuple[float, float],
        destino_coord: tuple[float, float],
    ) -> tuple[float, float]:
        cached = self.db.fetchone(
            "SELECT distancia_metros, tempo_segundos FROM matriz_distancia WHERE origem_id = ? AND destino_id = ?",
            (origem_id, destino_id),
        )
        if cached:
            return float(cached["distancia_metros"]), float(cached["tempo_segundos"])

        if not self.api_key:
            raise RuntimeError("ORS_API_KEY não configurada e rota não está em cache.")

        payload: dict[str, Any] = {
            "locations": [
                [origem_coord[1], origem_coord[0]],
                [destino_coord[1], destino_coord[0]],
            ],
            "metrics": ["distance", "duration"],
            "sources": [0],
            "destinations": [1],
        }

        try:
            response = requests.post(
                ORS_MATRIX_URL,
                json=payload,
                headers={"Authorization": self.api_key, "Content-Type": "application/json"},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            distancia = data["distances"][0][0]
            tempo = data["durations"][0][0]
            self.db.execute(
                """
                INSERT OR REPLACE INTO matriz_distancia (
                    origem_id, destino_id, distancia_metros, tempo_segundos, ultima_atualizacao
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (origem_id, destino_id, distancia, tempo, dt.datetime.now().isoformat()),
            )
            return float(distancia), float(tempo)
        except requests.RequestException as exc:
            raise RuntimeError(f"Falha ao consultar matriz ORS: {exc}") from exc

    def build_square_matrix(self, pontos: list[dict[str, Any]]) -> tuple[list[list[int]], list[list[int]]]:
        dist_matrix: list[list[int]] = []
        time_matrix: list[list[int]] = []

        for origem in pontos:
            dist_row: list[int] = []
            time_row: list[int] = []
            for destino in pontos:
                if origem["uid"] == destino["uid"]:
                    dist_row.append(0)
                    time_row.append(0)
                else:
                    d, t = self.get_distance_time(
                        origem["uid"], destino["uid"], origem["coord"], destino["coord"]
                    )
                    dist_row.append(int(d))
                    time_row.append(int(t))
            dist_matrix.append(dist_row)
            time_matrix.append(time_row)
        return dist_matrix, time_matrix
