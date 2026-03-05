"""Serviço de matriz dinâmica com cache persistente por pares."""

from __future__ import annotations

import datetime as dt
import os
from itertools import islice
from typing import Any, Iterable

import requests

from route_planner.database_manager import DatabaseManager


class MatrixService:
    def __init__(self, db: DatabaseManager, api_key: str | None = None, profile: str = "driving-car") -> None:
        self.db = db
        self.api_key = api_key or os.getenv("ORS_API_KEY", "")
        self.profile = profile

    def _chunks(self, data: list[int], size: int) -> Iterable[list[int]]:
        it = iter(data)
        while chunk := list(islice(it, size)):
            yield chunk

    def _cached_pairs(self, uids: list[str]) -> dict[tuple[str, str], tuple[float, float]]:
        placeholders = ",".join("?" for _ in uids)
        rows = self.db.fetchall(
            f"""
            SELECT origin_client_id, destination_client_id, distance_meters, duration_seconds
            FROM distance_cache
            WHERE profile = ?
              AND origin_client_id IN ({placeholders})
              AND destination_client_id IN ({placeholders})
            """,
            [self.profile, *uids, *uids],
        )
        return {
            (r["origin_client_id"], r["destination_client_id"]): (float(r["distance_meters"]), float(r["duration_seconds"]))
            for r in rows
        }

    def _fetch_block(self, points: list[dict[str, Any]], origin_idx: list[int], dest_idx: list[int]) -> dict[tuple[str, str], tuple[float, float]]:
        if not self.api_key:
            raise RuntimeError("ORS_API_KEY não configurada para completar pares ausentes")

        local = sorted(set(origin_idx + dest_idx))
        pos = {global_idx: i for i, global_idx in enumerate(local)}
        locations = [[points[i]["coord"][1], points[i]["coord"][0]] for i in local]
        payload = {
            "locations": locations,
            "sources": [pos[i] for i in origin_idx],
            "destinations": [pos[i] for i in dest_idx],
            "metrics": ["distance", "duration"],
        }
        resp = requests.post(
            f"https://api.openrouteservice.org/v2/matrix/{self.profile}",
            headers={"Authorization": self.api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        updates: dict[tuple[str, str], tuple[float, float]] = {}
        for i, gi in enumerate(origin_idx):
            for j, gj in enumerate(dest_idx):
                if gi == gj:
                    continue
                updates[(points[gi]["uid"], points[gj]["uid"])] = (float(data["distances"][i][j]), float(data["durations"][i][j]))
        return updates

    def build_square_matrix(self, points: list[dict[str, Any]]) -> tuple[list[list[int]], list[list[int]]]:
        uids = [p["uid"] for p in points]
        cache = self._cached_pairs(uids)
        missing = [(i, j) for i in range(len(points)) for j in range(len(points)) if i != j and (uids[i], uids[j]) not in cache]

        if missing:
            ids = list(range(len(points)))
            updates: dict[tuple[str, str], tuple[float, float]] = {}
            for o_chunk in self._chunks(ids, 40):
                for d_chunk in self._chunks(ids, 40):
                    block_needed = {(i, j) for i in o_chunk for j in d_chunk if i != j and (uids[i], uids[j]) not in cache}
                    if not block_needed:
                        continue
                    block_updates = self._fetch_block(points, o_chunk, d_chunk)
                    updates.update(block_updates)
                    cache.update(block_updates)

            now = dt.datetime.utcnow().isoformat()
            rows = [(o, d, v[0], v[1], self.profile, now) for (o, d), v in updates.items()]
            if rows:
                self.db.executemany(
                    """
                    INSERT INTO distance_cache (
                        origin_client_id, destination_client_id, distance_meters, duration_seconds, profile, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(origin_client_id, destination_client_id, profile) DO UPDATE SET
                        distance_meters=excluded.distance_meters,
                        duration_seconds=excluded.duration_seconds,
                        last_updated=excluded.last_updated
                    """,
                    rows,
                )

        dist, dur = [], []
        for i, oi in enumerate(uids):
            drow, trow = [], []
            for j, dj in enumerate(uids):
                if i == j:
                    drow.append(0)
                    trow.append(0)
                else:
                    d, t = cache[(oi, dj)]
                    drow.append(int(d))
                    trow.append(int(t))
            dist.append(drow)
            dur.append(trow)
        return dist, dur
