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
        ("Monday", "collect_monday"),
        ("Tuesday", "collect_tuesday"),
        ("Wednesday", "collect_wednesday"),
        ("Thursday", "collect_thursday"),
        ("Friday", "collect_friday"),
        ("Saturday", "collect_saturday"),
        ("Sunday", "collect_sunday"),
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

        self.nome = QLineEdit()
        self.endereco = QLineEdit()
        self.window_start = QComboBox()
        self.window_end = QComboBox()
        self.period = QComboBox()
        for h in range(6, 21):
            v = f"{h:02d}:00"
            self.window_start.addItem(v)
            self.window_end.addItem(v)
        self.period.addItems(["Morning", "Afternoon", "Night"])

        weekdays = QHBoxLayout()
        self.day_checks: dict[str, QCheckBox] = {}
        for label, field in self.DAYS:
            cb = QCheckBox(label)
            cb.setChecked(label not in ("Saturday", "Sunday"))
            self.day_checks[field] = cb
            weekdays.addWidget(cb)

        self.is_active = QCheckBox("Active")
        self.is_active.setChecked(True)

        form.addRow("Name", self.nome)
        form.addRow("Address", self.endereco)
        form.addRow("Window Start", self.window_start)
        form.addRow("Window End", self.window_end)
        form.addRow("Period", self.period)
        form.addRow(QLabel("Collection Days"), weekdays)
        form.addRow("Status", self.is_active)

        actions = QHBoxLayout()
        self.save_btn = QPushButton("Add Client")
        self.save_btn.clicked.connect(self.save)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_form)
        import_btn = QPushButton("Import CSV")
        import_btn.clicked.connect(self.import_csv)
        actions.addWidget(self.save_btn)
        actions.addWidget(clear_btn)
        actions.addWidget(import_btn)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Address", "Window", "Period", "Days", "Active", "Edit", "Delete"])

        root.addWidget(card)
        root.addLayout(actions)
        root.addWidget(self.table)
        self.refresh_table()

    def _days_text(self, row) -> str:
        labels = []
        for short, field in [("Mon", "collect_monday"), ("Tue", "collect_tuesday"), ("Wed", "collect_wednesday"), ("Thu", "collect_thursday"), ("Fri", "collect_friday"), ("Sat", "collect_saturday"), ("Sun", "collect_sunday")]:
            if row[field]:
                labels.append(short)
        return ",".join(labels)

    def clear_form(self) -> None:
        self.editing_id = None
        self.save_btn.setText("Add Client")
        self.nome.clear()
        self.endereco.clear()
        self.window_start.setCurrentText("08:00")
        self.window_end.setCurrentText("18:00")
        self.period.setCurrentText("Morning")
        self.is_active.setChecked(True)

    def save(self) -> None:
        if not self.nome.text().strip() or not self.endereco.text().strip():
            QMessageBox.warning(self, "Validation", "Name and Address are required.")
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
                    VALUES (?, ?, ?, ?, '08:00', '18:00', 'Morning', 1)
                    """,
                    (row.get("name") or row.get("nome") or "Unnamed", endereco, lat, lon),
                )
        self.refresh_table()

    def edit_client(self, client_id: int) -> None:
        r = self.db.fetchone("SELECT * FROM clientes WHERE id=?", (client_id,))
        if not r:
            return
        self.editing_id = client_id
        self.save_btn.setText("Update Client")
        self.nome.setText(r["nome"])
        self.endereco.setText(r["endereco"])
        self.window_start.setCurrentText(r["window_start"] or "08:00")
        self.window_end.setCurrentText(r["window_end"] or "18:00")
        self.period.setCurrentText(r["period"] or "Morning")
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
            self.table.setItem(i, 6, QTableWidgetItem("Yes" if row["is_active"] else "No"))
            edit = QPushButton("Edit")
            edit.clicked.connect(lambda _=False, cid=row["id"]: self.edit_client(cid))
            toggle = QPushButton("Activate/Deactivate")
            toggle.clicked.connect(lambda _=False, cid=row["id"]: self.toggle_active(cid))
            delete = QPushButton("Delete")
            delete.clicked.connect(lambda _=False, cid=row["id"]: self.delete_client(cid))
            wrap = QWidget()
            hl = QHBoxLayout(wrap)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.addWidget(edit)
            hl.addWidget(toggle)
            self.table.setCellWidget(i, 7, wrap)
            self.table.setCellWidget(i, 8, delete)
