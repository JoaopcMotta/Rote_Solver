from __future__ import annotations

import csv

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
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
    DAYS = [
        ("Segunda", "collect_monday"),
        ("Terça", "collect_tuesday"),
        ("Quarta", "collect_wednesday"),
        ("Quinta", "collect_thursday"),
        ("Sexta", "collect_friday"),
        ("Sábado", "collect_saturday"),
        ("Domingo", "collect_sunday"),
    ]

    def __init__(self, db: DatabaseManager, geocode: GeocodeService) -> None:
        super().__init__()
        self.db = db
        self.geocode = geocode
        self.editing_id: int | None = None

        root = QVBoxLayout(self)
        card = QFrame()
        card.setObjectName("Card")
        form = QFormLayout(card)
        form.setSpacing(10)

        self.nome = QLineEdit()
        self.endereco = QLineEdit()
        self.window_start = QComboBox()
        self.window_end = QComboBox()
        self.period = QComboBox()
        for h in range(6, 21):
            hora = f"{h:02d}:00"
            self.window_start.addItem(hora)
            self.window_end.addItem(hora)
        self.period.addItems(["Manhã", "Tarde", "Noite"])

        days_layout = QHBoxLayout()
        self.day_checks: dict[str, QCheckBox] = {}
        for label, field in self.DAYS:
            cb = QCheckBox(label)
            cb.setChecked(label not in ("Sábado", "Domingo"))
            self.day_checks[field] = cb
            days_layout.addWidget(cb)

        self.is_active = QCheckBox("Ativo")
        self.is_active.setChecked(True)

        form.addRow("Nome", self.nome)
        form.addRow("Endereço", self.endereco)
        form.addRow("Início da Janela", self.window_start)
        form.addRow("Fim da Janela", self.window_end)
        form.addRow("Período", self.period)
        form.addRow(QLabel("Dias de Coleta"), days_layout)
        form.addRow("Status", self.is_active)

        actions = QHBoxLayout()
        self.save_btn = QPushButton("Adicionar Cliente")
        self.save_btn.clicked.connect(self.save)
        clear_btn = QPushButton("Limpar")
        clear_btn.clicked.connect(self.clear_form)
        import_btn = QPushButton("Importar CSV")
        import_btn.clicked.connect(self.import_csv)
        actions.addWidget(self.save_btn)
        actions.addWidget(clear_btn)
        actions.addWidget(import_btn)

        self.table = QTableWidget(0, 9)
        self.table.setAlternatingRowColors(True)
        self.table.setHorizontalHeaderLabels(["ID", "Nome", "Endereço", "Janela", "Período", "Dias", "Ativo", "Editar", "Excluir"])

        root.addWidget(card)
        root.addLayout(actions)
        root.addWidget(self.table)
        self.refresh_table()

    def _days_text(self, row) -> str:
        labels = []
        for short, field in [("Seg", "collect_monday"), ("Ter", "collect_tuesday"), ("Qua", "collect_wednesday"), ("Qui", "collect_thursday"), ("Sex", "collect_friday"), ("Sáb", "collect_saturday"), ("Dom", "collect_sunday")]:
            if row[field]:
                labels.append(short)
        return ",".join(labels)

    def clear_form(self) -> None:
        self.editing_id = None
        self.save_btn.setText("Adicionar Cliente")
        self.nome.clear()
        self.endereco.clear()
        self.window_start.setCurrentText("08:00")
        self.window_end.setCurrentText("18:00")
        self.period.setCurrentText("Manhã")
        self.is_active.setChecked(True)

    def save(self) -> None:
        if not self.nome.text().strip() or not self.endereco.text().strip():
            QMessageBox.warning(self, "Validação", "Nome e Endereço são obrigatórios.")
            return

        coords = self.geocode.geocode(self.endereco.text().strip())
        lat, lon = coords if coords else (None, None)
        day_values = [1 if self.day_checks[field].isChecked() else 0 for _, field in self.DAYS]

        data = (
            self.nome.text().strip(),
            self.endereco.text().strip(),
            lat,
            lon,
            self.window_start.currentText(),
            self.window_end.currentText(),
            self.period.currentText(),
            1 if self.is_active.isChecked() else 0,
            *day_values,
        )

        if self.editing_id is None:
            self.db.execute(
                """
                INSERT INTO clientes (
                    nome, endereco, latitude, longitude, window_start, window_end, period, is_active,
                    collect_monday, collect_tuesday, collect_wednesday, collect_thursday,
                    collect_friday, collect_saturday, collect_sunday
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data,
            )
        else:
            self.db.execute(
                """
                UPDATE clientes SET
                    nome=?, endereco=?, latitude=?, longitude=?, window_start=?, window_end=?, period=?, is_active=?,
                    collect_monday=?, collect_tuesday=?, collect_wednesday=?, collect_thursday=?,
                    collect_friday=?, collect_saturday=?, collect_sunday=?
                WHERE id=?
                """,
                (*data, self.editing_id),
            )

        self.clear_form()
        self.refresh_table()

    def import_csv(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(self, "Selecionar CSV", "", "CSV (*.csv)")
        if not file_name:
            return
        with open(file_name, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                endereco = row.get("address") or row.get("endereco") or ""
                coords = self.geocode.geocode(endereco)
                lat, lon = coords if coords else (None, None)
                self.db.execute(
                    """
                    INSERT INTO clientes(nome, endereco, latitude, longitude, window_start, window_end, period, is_active)
                    VALUES (?, ?, ?, ?, '08:00', '18:00', 'Manhã', 1)
                    """,
                    (row.get("name") or row.get("nome") or "Sem nome", endereco, lat, lon),
                )
        self.refresh_table()

    def edit_client(self, client_id: int) -> None:
        r = self.db.fetchone("SELECT * FROM clientes WHERE id=?", (client_id,))
        if not r:
            return
        self.editing_id = client_id
        self.save_btn.setText("Atualizar Cliente")
        self.nome.setText(r["nome"])
        self.endereco.setText(r["endereco"])
        self.window_start.setCurrentText(r["window_start"] or "08:00")
        self.window_end.setCurrentText(r["window_end"] or "18:00")
        self.period.setCurrentText(r["period"] or "Manhã")
        self.is_active.setChecked(bool(r["is_active"]))
        for _, field in self.DAYS:
            self.day_checks[field].setChecked(bool(r[field]))

    def toggle_active(self, client_id: int) -> None:
        self.db.execute("UPDATE clientes SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id=?", (client_id,))
        self.refresh_table()

    def delete_client(self, client_id: int) -> None:
        self.db.execute("DELETE FROM clientes WHERE id=?", (client_id,))
        self.refresh_table()

    def refresh_table(self) -> None:
        rows = self.db.fetchall("SELECT * FROM clientes ORDER BY id DESC")
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(row["nome"]))
            self.table.setItem(i, 2, QTableWidgetItem(row["endereco"]))
            self.table.setItem(i, 3, QTableWidgetItem(f"{row['window_start']}-{row['window_end']}"))
            self.table.setItem(i, 4, QTableWidgetItem(row["period"] or ""))
            self.table.setItem(i, 5, QTableWidgetItem(self._days_text(row)))
            self.table.setItem(i, 6, QTableWidgetItem("Ativo" if row["is_active"] else "Inativo"))
            edit = QPushButton("Editar")
            edit.clicked.connect(lambda _=False, cid=row["id"]: self.edit_client(cid))
            toggle = QPushButton("Ativar/Desativar")
            toggle.clicked.connect(lambda _=False, cid=row["id"]: self.toggle_active(cid))
            delete = QPushButton("Excluir")
            delete.clicked.connect(lambda _=False, cid=row["id"]: self.delete_client(cid))
            wrap = QWidget()
            hl = QHBoxLayout(wrap)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.addWidget(edit)
            hl.addWidget(toggle)
            self.table.setCellWidget(i, 7, wrap)
            self.table.setCellWidget(i, 8, delete)
