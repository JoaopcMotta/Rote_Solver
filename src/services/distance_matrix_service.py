"""Dynamic distance matrix builder backed by persistent pairwise cache."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.openrouteservice_client import OpenRouteServiceClient


class DistanceMatrixService:
    """Builds OR-Tools compatible distance and duration matrices.

    Strategy:
    1) Ensure client coordinates exist (geocode missing ones).
    2) Read cached pairwise entries from ``distance_cache``.
    3) Request only missing origin/destination pairs in batched ORS matrix calls.
    4) Persist newly fetched pairs and build matrix in-memory.
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        ors_client: OpenRouteServiceClient,
        profile: str = "driving-car",
        batch_size: int = 50,
    ) -> None:
        self.conn = conn
        self.ors = ors_client
        self.profile = profile
        self.batch_size = max(1, batch_size)

    def build_for_client_ids(
        self, client_ids: list[int]
    ) -> tuple[list[list[int]], list[list[int]], dict[int, int]]:
        """Return (distance_matrix, duration_matrix, client_id_to_node_index)."""
        unique_ids = list(dict.fromkeys(client_ids))
        if not unique_ids:
            return [], [], {}

        clients = self._load_clients(unique_ids)
        self._ensure_geocoded(clients)

        cache = self._load_cache(unique_ids)
        missing_pairs = self._get_missing_pairs(unique_ids, cache)
        if missing_pairs:
            fetched = self._fetch_missing_pairs(unique_ids, clients, missing_pairs)
            cache.update(fetched)
            self._persist_pairs(fetched)

        index_map = {client_id: idx for idx, client_id in enumerate(unique_ids)}
        n = len(unique_ids)
        dist = [[0] * n for _ in range(n)]
        dur = [[0] * n for _ in range(n)]

        for i, origin_id in enumerate(unique_ids):
            for j, destination_id in enumerate(unique_ids):
                if i == j:
                    continue
                d, t = cache[(origin_id, destination_id)]
                dist[i][j] = int(d)
                dur[i][j] = int(t)

        return dist, dur, index_map

    def _load_clients(self, client_ids: list[int]) -> dict[int, sqlite3.Row]:
        placeholders = ",".join("?" for _ in client_ids)
        rows = self.conn.execute(
            f"SELECT id, address, latitude, longitude FROM clients WHERE id IN ({placeholders})", client_ids
        ).fetchall()
        by_id = {int(row["id"]): row for row in rows}
        missing = [cid for cid in client_ids if cid not in by_id]
        if missing:
            raise ValueError(f"Clientes não encontrados: {missing}")
        return by_id

    def _ensure_geocoded(self, clients: dict[int, sqlite3.Row]) -> None:
        updates: list[tuple[float, float, int]] = []
        for client_id, row in clients.items():
            if row["latitude"] is not None and row["longitude"] is not None:
                continue
            coords = self.ors.geocode(row["address"])
            if not coords:
                raise RuntimeError(
                    f"Cliente {client_id} sem coordenadas e geocodificação indisponível para '{row['address']}'."
                )
            lat, lon = coords
            updates.append((lat, lon, client_id))

        if updates:
            self.conn.executemany("UPDATE clients SET latitude = ?, longitude = ? WHERE id = ?", updates)
            self.conn.commit()

    def _load_cache(self, client_ids: list[int]) -> dict[tuple[int, int], tuple[float, float]]:
        placeholders = ",".join("?" for _ in client_ids)
        rows = self.conn.execute(
            f"""
            SELECT origin_client_id, destination_client_id, distance_meters, duration_seconds
            FROM distance_cache
            WHERE profile = ?
              AND origin_client_id IN ({placeholders})
              AND destination_client_id IN ({placeholders})
            """,
            [self.profile, *client_ids, *client_ids],
        ).fetchall()
        return {
            (int(r["origin_client_id"]), int(r["destination_client_id"])): (
                float(r["distance_meters"]),
                float(r["duration_seconds"]),
            )
            for r in rows
        }

    @staticmethod
    def _get_missing_pairs(
        client_ids: list[int], cache: dict[tuple[int, int], tuple[float, float]]
    ) -> set[tuple[int, int]]:
        missing: set[tuple[int, int]] = set()
        for origin in client_ids:
            for dest in client_ids:
                if origin == dest:
                    continue
                if (origin, dest) not in cache:
                    missing.add((origin, dest))
        return missing

    def _fetch_missing_pairs(
        self,
        client_ids: list[int],
        clients: dict[int, sqlite3.Row],
        missing_pairs: set[tuple[int, int]],
    ) -> dict[tuple[int, int], tuple[float, float]]:
        if not self.ors.enabled:
            raise RuntimeError("Pares ausentes no cache e ORS_API_KEY não configurada.")

        fetched: dict[tuple[int, int], tuple[float, float]] = {}
        ids = list(client_ids)

        for origin_chunk in self._chunks(ids, self.batch_size):
            for dest_chunk in self._chunks(ids, self.batch_size):
                block_pairs = {
                    (o, d)
                    for o in origin_chunk
                    for d in dest_chunk
                    if o != d and (o, d) in missing_pairs
                }
                if not block_pairs:
                    continue

                local_ids = list(dict.fromkeys([*origin_chunk, *dest_chunk]))
                local_idx = {cid: idx for idx, cid in enumerate(local_ids)}
                coordinates = [
                    (float(clients[cid]["latitude"]), float(clients[cid]["longitude"])) for cid in local_ids
                ]
                sources = [local_idx[cid] for cid in origin_chunk]
                destinations = [local_idx[cid] for cid in dest_chunk]

                payload = self.ors.matrix(
                    coordinates=coordinates,
                    sources=sources,
                    destinations=destinations,
                    profile=self.profile,
                )
                distances = payload.get("distances", [])
                durations = payload.get("durations", [])

                for i, origin_id in enumerate(origin_chunk):
                    for j, dest_id in enumerate(dest_chunk):
                        if origin_id == dest_id:
                            continue
                        if (origin_id, dest_id) not in block_pairs:
                            continue
                        fetched[(origin_id, dest_id)] = (
                            float(distances[i][j]),
                            float(durations[i][j]),
                        )

        unresolved = missing_pairs - set(fetched)
        if unresolved:
            raise RuntimeError(f"Não foi possível obter todos os pares ausentes. Total pendente: {len(unresolved)}")

        return fetched

    def _persist_pairs(self, pairs: dict[tuple[int, int], tuple[float, float]]) -> None:
        if not pairs:
            return
        now = datetime.utcnow().isoformat()
        rows = [
            (origin, dest, dist, dur, self.profile, now)
            for (origin, dest), (dist, dur) in pairs.items()
        ]
        self.conn.executemany(
            """
            INSERT INTO distance_cache (
                origin_client_id,
                destination_client_id,
                distance_meters,
                duration_seconds,
                profile,
                last_updated
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(origin_client_id, destination_client_id, profile)
            DO UPDATE SET
                distance_meters=excluded.distance_meters,
                duration_seconds=excluded.duration_seconds,
                last_updated=excluded.last_updated
            """,
            rows,
        )
        self.conn.commit()

    @staticmethod
    def _chunks(items: list[int], size: int) -> Iterable[list[int]]:
        for i in range(0, len(items), size):
            yield items[i : i + size]
