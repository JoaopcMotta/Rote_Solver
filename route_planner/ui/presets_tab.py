from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from route_planner.database_manager import DatabaseManager


class PresetsTab(QWidget):
    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        self.db = db
        layout = QVBoxLayout(self)

        box = QGroupBox("Novo preset")
        form = QFormLayout(box)
        self.nome = QLineEdit()
        self.time_limit = QLineEdit("30")
        self.penalty = QLineEdit("10000")
        self.service = QLineEdit("600")
        form.addRow("Nome", self.nome)
        form.addRow("Tempo limite (s)", self.time_limit)
        form.addRow("Penalidade", self.penalty)
        form.addRow("Tempo parada (s)", self.service)

        btn = QPushButton("Salvar preset")
        btn.clicked.connect(self.save)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Nome", "Tempo", "Penalidade"])

        layout.addWidget(box)
        layout.addWidget(btn)
        layout.addWidget(self.table)
        self.refresh()

    def save(self) -> None:
        self.db.execute(
            """
            INSERT INTO presets_solver (
                nome, tempo_limite_segundos, first_solution_strategy,
                local_search_metaheuristic, penalidade_cliente_nao_visitado,
                tempo_parada_padrao_segundos
            ) VALUES (?, ?, 'PARALLEL_CHEAPEST_INSERTION', 'GUIDED_LOCAL_SEARCH', ?, ?)
            """,
            (self.nome.text(), int(self.time_limit.text()), int(self.penalty.text()), int(self.service.text())),
        )
        self.refresh()

    def refresh(self) -> None:
        rows = self.db.fetchall("SELECT id, nome, tempo_limite_segundos, penalidade_cliente_nao_visitado FROM presets_solver ORDER BY id")
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(row["nome"]))
            self.table.setItem(i, 2, QTableWidgetItem(str(row["tempo_limite_segundos"])))
            self.table.setItem(i, 3, QTableWidgetItem(str(row["penalidade_cliente_nao_visitado"])))
