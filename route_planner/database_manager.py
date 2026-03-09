"""Camada de banco de dados SQLite para o planejador de rotas."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable

DB_PATH = Path(__file__).resolve().parent / "database" / "db.sqlite"


class DatabaseManager:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        c = self.conn.cursor()

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                endereco TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                window_start TEXT DEFAULT '08:00',
                window_end TEXT DEFAULT '18:00',
                period TEXT DEFAULT 'Morning',
                is_active INTEGER NOT NULL DEFAULT 1,
                collect_monday INTEGER NOT NULL DEFAULT 1,
                collect_tuesday INTEGER NOT NULL DEFAULT 1,
                collect_wednesday INTEGER NOT NULL DEFAULT 1,
                collect_thursday INTEGER NOT NULL DEFAULT 1,
                collect_friday INTEGER NOT NULL DEFAULT 1,
                collect_saturday INTEGER NOT NULL DEFAULT 0,
                collect_sunday INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS veiculos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                departure TEXT NOT NULL,
                destination TEXT NOT NULL,
                departure_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                capacidade INTEGER,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS distance_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origin_client_id TEXT NOT NULL,
                destination_client_id TEXT NOT NULL,
                distance_meters REAL NOT NULL,
                duration_seconds REAL NOT NULL,
                profile TEXT NOT NULL DEFAULT 'driving-car',
                last_updated TEXT NOT NULL,
                UNIQUE(origin_client_id, destination_client_id, profile)
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS presets_solver (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preset_name TEXT NOT NULL UNIQUE,
                time_limit_seconds INTEGER NOT NULL DEFAULT 30,
                stop_time_minutes INTEGER NOT NULL DEFAULT 10,
                penalty_value INTEGER NOT NULL DEFAULT 10000,
                first_solution_strategy TEXT NOT NULL DEFAULT 'PARALLEL_CHEAPEST_INSERTION',
                local_search_metaheuristic TEXT NOT NULL DEFAULT 'GUIDED_LOCAL_SEARCH',
                solution_limit INTEGER,
                log_search INTEGER NOT NULL DEFAULT 0,
                use_full_propagation INTEGER NOT NULL DEFAULT 1
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS rotas_calculadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_calculo TEXT NOT NULL,
                dia_semana TEXT NOT NULL,
                preset_id INTEGER NOT NULL,
                vehicles_used TEXT,
                route_summary TEXT,
                map_payload TEXT,
                distancia_total REAL NOT NULL,
                tempo_total REAL NOT NULL,
                FOREIGN KEY (preset_id) REFERENCES presets_solver(id)
            )
            """
        )

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS rota_paradas (
                rota_id INTEGER NOT NULL,
                veiculo_id INTEGER NOT NULL,
                ordem INTEGER NOT NULL,
                cliente_id INTEGER,
                tempo_chegada TEXT,
                distancia_acumulada REAL,
                PRIMARY KEY (rota_id, veiculo_id, ordem),
                FOREIGN KEY (rota_id) REFERENCES rotas_calculadas(id),
                FOREIGN KEY (veiculo_id) REFERENCES veiculos(id),
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
            """
        )

        self._ensure_column("presets_solver", "preset_name", "TEXT")
        self._ensure_column("clientes", "window_start", "TEXT DEFAULT '08:00'")
        self._ensure_column("clientes", "window_end", "TEXT DEFAULT '18:00'")
        self._ensure_column("clientes", "period", "TEXT DEFAULT 'Morning'")
        self._ensure_column("clientes", "is_active", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column("clientes", "collect_sunday", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column("veiculos", "departure", "TEXT")
        self._ensure_column("veiculos", "destination", "TEXT")
        self._ensure_column("veiculos", "departure_time", "TEXT")
        self._ensure_column("veiculos", "end_time", "TEXT")
        self._ensure_column("veiculos", "is_active", "INTEGER NOT NULL DEFAULT 1")
        self._ensure_column("rotas_calculadas", "vehicles_used", "TEXT")
        self._ensure_column("rotas_calculadas", "route_summary", "TEXT")
        self._ensure_column("rotas_calculadas", "map_payload", "TEXT")

        c.execute(
            """
            INSERT OR IGNORE INTO presets_solver (
                preset_name, time_limit_seconds, stop_time_minutes, penalty_value,
                first_solution_strategy, local_search_metaheuristic
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "Rota padrão lavanderia",
                30,
                10,
                10000,
                "PARALLEL_CHEAPEST_INSERTION",
                "GUIDED_LOCAL_SEARCH",
            ),
        )
        self.conn.commit()

    def _ensure_column(self, table: str, column: str, col_type: str) -> None:
        cols = {r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in cols:
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

    def execute(self, query: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        cur = self.conn.cursor()
        cur.execute(query, params)
        self.conn.commit()
        return cur

    def executemany(self, query: str, params: Iterable[Iterable[Any]]) -> None:
        self.conn.executemany(query, params)
        self.conn.commit()

    def fetchall(self, query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        return list(self.conn.execute(query, params).fetchall())

    def fetchone(self, query: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        return self.conn.execute(query, params).fetchone()
