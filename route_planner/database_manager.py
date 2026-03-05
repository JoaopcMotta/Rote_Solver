"""Camada de banco de dados SQLite para o planejador de rotas."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable

DB_PATH = Path(__file__).resolve().parent / "database" / "db.sqlite"


class DatabaseManager:
    """Gerencia conexão e inicialização do banco SQLite."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        cursor = self.conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                endereco TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                ativo INTEGER NOT NULL DEFAULT 1,
                segunda INTEGER NOT NULL DEFAULT 1,
                terca INTEGER NOT NULL DEFAULT 1,
                quarta INTEGER NOT NULL DEFAULT 1,
                quinta INTEGER NOT NULL DEFAULT 1,
                sexta INTEGER NOT NULL DEFAULT 1,
                sabado INTEGER NOT NULL DEFAULT 0,
                hora_inicio TEXT,
                hora_fim TEXT,
                periodo TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS veiculos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                endereco_inicio TEXT NOT NULL,
                endereco_fim TEXT NOT NULL,
                hora_inicio TEXT NOT NULL,
                hora_fim TEXT NOT NULL,
                capacidade INTEGER NOT NULL DEFAULT 0,
                ativo INTEGER NOT NULL DEFAULT 1
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS matriz_distancia (
                origem_id TEXT NOT NULL,
                destino_id TEXT NOT NULL,
                distancia_metros REAL NOT NULL,
                tempo_segundos REAL NOT NULL,
                ultima_atualizacao TEXT NOT NULL,
                PRIMARY KEY (origem_id, destino_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS presets_solver (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                tempo_limite_segundos INTEGER NOT NULL DEFAULT 30,
                solucao_limite INTEGER,
                lns_tempo_limite INTEGER,
                first_solution_strategy TEXT NOT NULL,
                local_search_metaheuristic TEXT NOT NULL,
                usar_relocate INTEGER NOT NULL DEFAULT 1,
                usar_exchange INTEGER NOT NULL DEFAULT 1,
                usar_2opt INTEGER NOT NULL DEFAULT 1,
                usar_oropt INTEGER NOT NULL DEFAULT 1,
                usar_cross INTEGER NOT NULL DEFAULT 0,
                usar_lns INTEGER NOT NULL DEFAULT 1,
                use_full_propagation INTEGER NOT NULL DEFAULT 1,
                penalidade_cliente_nao_visitado INTEGER NOT NULL DEFAULT 10000,
                tempo_parada_padrao_segundos INTEGER NOT NULL DEFAULT 600,
                balancear_rotas INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rotas_calculadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_calculo TEXT NOT NULL,
                dia_semana TEXT NOT NULL,
                preset_id INTEGER NOT NULL,
                distancia_total REAL NOT NULL,
                tempo_total REAL NOT NULL,
                FOREIGN KEY (preset_id) REFERENCES presets_solver(id)
            )
            """
        )

        cursor.execute(
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

        cursor.execute(
            """
            INSERT OR IGNORE INTO presets_solver (
                nome,
                tempo_limite_segundos,
                first_solution_strategy,
                local_search_metaheuristic,
                penalidade_cliente_nao_visitado,
                tempo_parada_padrao_segundos
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "Rota padrão lavanderia",
                30,
                "PARALLEL_CHEAPEST_INSERTION",
                "GUIDED_LOCAL_SEARCH",
                10000,
                600,
            ),
        )

        self.conn.commit()

    def execute(self, query: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor

    def fetchall(self, query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        return list(self.conn.execute(query, params).fetchall())

    def fetchone(self, query: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        return self.conn.execute(query, params).fetchone()
