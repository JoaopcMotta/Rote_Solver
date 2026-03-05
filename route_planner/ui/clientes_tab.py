from __future__ import annotations

import csv
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from route_planner.database_manager import DatabaseManager
from route_planner.services.geocode_service import GeocodeService


class ClientesTab(QWidget):
    def __init__(self, db: DatabaseManager, geocode: GeocodeService) -> None:
        super().__init__()
        self.db = db
        self.geocode = geocode

        layout = QVBoxLayout(self)
        form_box = QGroupBox("Cadastro de cliente")
        form = QFormLayout(form_box)
        self.nome = QLineEdit()
        self.endereco = QLineEdit()
        self.hora_inicio = QLineEdit("08:00")
        self.hora_fim = QLineEdit("18:00")
        self.periodo = QLineEdit("manhã")
        form.addRow("Nome", self.nome)
        form.addRow("Endereço", self.endereco)
        form.addRow("Hora início", self.hora_inicio)
        form.addRow("Hora fim", self.hora_fim)
        form.addRow("Período", self.periodo)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Adicionar cliente")
        save_btn.clicked.connect(self.save_cliente)
        import_btn = QPushButton("Importar CSV")
        import_btn.clicked.connect(self.import_csv)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(import_btn)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Nome", "Endereço", "Lat", "Lon"])

        layout.addWidget(form_box)
        layout.addLayout(btn_row)
        layout.addWidget(self.table)
        self.refresh_table()

    def save_cliente(self) -> None:
        nome = self.nome.text().strip()
        endereco = self.endereco.text().strip()
        if not nome or not endereco:
            QMessageBox.warning(self, "Validação", "Nome e endereço são obrigatórios.")
            return

        coords = self.geocode.geocode(endereco)
        lat, lon = (coords if coords else (None, None))
        self.db.execute(
            """
            INSERT INTO clientes (
                nome, endereco, latitude, longitude, ativo,
                segunda, terca, quarta, quinta, sexta, sabado,
                hora_inicio, hora_fim, periodo
            ) VALUES (?, ?, ?, ?, 1, 1, 1, 1, 1, 1, 0, ?, ?, ?)
            """,
            (nome, endereco, lat, lon, self.hora_inicio.text(), self.hora_fim.text(), self.periodo.text()),
        )
        self.refresh_table()

    def import_csv(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, "Selecionar CSV", "", "CSV (*.csv)")
        if not file_name:
            return

        with Path(file_name).open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                endereco = row.get("endereco", "")
                coords = self.geocode.geocode(endereco)
                lat, lon = (coords if coords else (None, None))
                self.db.execute(
                    "INSERT INTO clientes (nome, endereco, latitude, longitude, ativo) VALUES (?, ?, ?, ?, 1)",
                    (row.get("nome", "Sem nome"), endereco, lat, lon),
                )
        self.refresh_table()

    def refresh_table(self) -> None:
        rows = self.db.fetchall("SELECT id, nome, endereco, latitude, longitude FROM clientes ORDER BY id DESC")
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(row["nome"]))
            self.table.setItem(i, 2, QTableWidgetItem(row["endereco"]))
            self.table.setItem(i, 3, QTableWidgetItem(str(row["latitude"])))
            self.table.setItem(i, 4, QTableWidgetItem(str(row["longitude"])))
