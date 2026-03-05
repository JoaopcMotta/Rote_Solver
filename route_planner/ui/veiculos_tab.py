from __future__ import annotations

from PySide6.QtWidgets import (
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


class VeiculosTab(QWidget):
    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        self.db = db

        layout = QVBoxLayout(self)
        box = QGroupBox("Cadastro de veículo")
        form = QFormLayout(box)
        self.nome = QLineEdit()
        self.end_inicio = QLineEdit()
        self.end_fim = QLineEdit()
        self.hora_inicio = QLineEdit("07:00")
        self.hora_fim = QLineEdit("19:00")
        self.cap = QLineEdit("100")

        form.addRow("Nome", self.nome)
        form.addRow("Endereço início", self.end_inicio)
        form.addRow("Endereço fim", self.end_fim)
        form.addRow("Hora início", self.hora_inicio)
        form.addRow("Hora fim", self.hora_fim)
        form.addRow("Capacidade", self.cap)

        btn = QPushButton("Adicionar veículo")
        btn.clicked.connect(self.save)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Nome", "Início", "Fim", "Capacidade"])

        layout.addWidget(box)
        layout.addWidget(btn)
        layout.addWidget(self.table)
        self.refresh()

    def save(self) -> None:
        if not self.nome.text().strip():
            QMessageBox.warning(self, "Validação", "Nome é obrigatório")
            return
        self.db.execute(
            """
            INSERT INTO veiculos (nome, endereco_inicio, endereco_fim, hora_inicio, hora_fim, capacidade, ativo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                self.nome.text(),
                self.end_inicio.text(),
                self.end_fim.text(),
                self.hora_inicio.text(),
                self.hora_fim.text(),
                int(self.cap.text() or 0),
            ),
        )
        self.refresh()

    def refresh(self) -> None:
        rows = self.db.fetchall("SELECT id, nome, endereco_inicio, endereco_fim, capacidade FROM veiculos ORDER BY id DESC")
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(row["nome"]))
            self.table.setItem(i, 2, QTableWidgetItem(row["endereco_inicio"]))
            self.table.setItem(i, 3, QTableWidgetItem(row["endereco_fim"]))
            self.table.setItem(i, 4, QTableWidgetItem(str(row["capacidade"])))
