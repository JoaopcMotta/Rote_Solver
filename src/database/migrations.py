"""Schema initialization and lightweight migrations."""

from __future__ import annotations

import sqlite3
from typing import Iterable

DEFAULT_PRESET_NAME = "Rota padrão lavanderia"

SCHEMA_STATEMENTS: Iterable[str] = (
    """
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        active INTEGER NOT NULL DEFAULT 1,
        monday INTEGER NOT NULL DEFAULT 1,
        tuesday INTEGER NOT NULL DEFAULT 1,
        wednesday INTEGER NOT NULL DEFAULT 1,
        thursday INTEGER NOT NULL DEFAULT 1,
        friday INTEGER NOT NULL DEFAULT 1,
        saturday INTEGER NOT NULL DEFAULT 0,
        sunday INTEGER NOT NULL DEFAULT 0,
        time_window_start TEXT,
        time_window_end TEXT,
        period TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        start_address TEXT NOT NULL,
        end_address TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        capacity INTEGER NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS solver_presets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        time_limit_seconds INTEGER NOT NULL DEFAULT 30,
        solution_limit INTEGER,
        lns_time_limit INTEGER,
        first_solution_strategy TEXT NOT NULL DEFAULT 'PARALLEL_CHEAPEST_INSERTION',
        local_search_metaheuristic TEXT NOT NULL DEFAULT 'GUIDED_LOCAL_SEARCH',
        use_relocate INTEGER NOT NULL DEFAULT 1,
        use_exchange INTEGER NOT NULL DEFAULT 1,
        use_2opt INTEGER NOT NULL DEFAULT 1,
        use_oropt INTEGER NOT NULL DEFAULT 1,
        use_cross INTEGER NOT NULL DEFAULT 0,
        use_lns INTEGER NOT NULL DEFAULT 1,
        use_full_propagation INTEGER NOT NULL DEFAULT 1,
        unserved_customer_penalty INTEGER NOT NULL DEFAULT 10000,
        default_service_time_seconds INTEGER NOT NULL DEFAULT 600,
        balance_routes INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS distance_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        origin_client_id INTEGER NOT NULL,
        destination_client_id INTEGER NOT NULL,
        distance_meters REAL NOT NULL,
        duration_seconds REAL NOT NULL,
        profile TEXT NOT NULL DEFAULT 'driving-car',
        last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(origin_client_id, destination_client_id, profile),
        FOREIGN KEY(origin_client_id) REFERENCES clients(id),
        FOREIGN KEY(destination_client_id) REFERENCES clients(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS computed_routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        calculation_time TEXT NOT NULL,
        weekday TEXT NOT NULL,
        preset_id INTEGER NOT NULL,
        total_distance REAL NOT NULL,
        total_duration REAL NOT NULL,
        FOREIGN KEY(preset_id) REFERENCES solver_presets(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS route_stops (
        route_id INTEGER NOT NULL,
        vehicle_id INTEGER NOT NULL,
        stop_order INTEGER NOT NULL,
        client_id INTEGER,
        arrival_time TEXT,
        cumulative_distance REAL,
        PRIMARY KEY(route_id, vehicle_id, stop_order),
        FOREIGN KEY(route_id) REFERENCES computed_routes(id),
        FOREIGN KEY(vehicle_id) REFERENCES vehicles(id),
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_distance_cache_profile ON distance_cache(profile)",
    "CREATE INDEX IF NOT EXISTS idx_distance_cache_origin ON distance_cache(origin_client_id)",
    "CREATE INDEX IF NOT EXISTS idx_distance_cache_destination ON distance_cache(destination_client_id)",
)


def initialize_database(conn: sqlite3.Connection) -> None:
    """Create schema and seed default records."""
    cur = conn.cursor()
    for stmt in SCHEMA_STATEMENTS:
        cur.execute(stmt)

    cur.execute(
        """
        INSERT OR IGNORE INTO solver_presets (
            name,
            time_limit_seconds,
            first_solution_strategy,
            local_search_metaheuristic,
            unserved_customer_penalty,
            default_service_time_seconds
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            DEFAULT_PRESET_NAME,
            30,
            "PARALLEL_CHEAPEST_INSERTION",
            "GUIDED_LOCAL_SEARCH",
            10000,
            600,
        ),
    )
    conn.commit()
