from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
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
        self.editing_id: int | None = None

        root = QVBoxLayout(self)
        card = QFrame()
        form = QFormLayout(card)
        self.nome = QLineEdit()
        self.departure = QLineEdit()
        self.destination = QLineEdit()
        self.departure_time = QComboBox()
        self.end_time = QComboBox()
        for h in range(6, 21):
            v = f"{h:02d}:00"
            self.departure_time.addItem(v)
            self.end_time.addItem(v)

        form.addRow("Name", self.nome)
        form.addRow("Departure", self.departure)
        form.addRow("Destination", self.destination)
        form.addRow("Departure Time", self.departure_time)
        form.addRow("End Time", self.end_time)

        actions = QHBoxLayout()
        self.save_btn = QPushButton("Add Vehicle")
        self.save_btn.clicked.connect(self.save)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_form)
        actions.addWidget(self.save_btn)
        actions.addWidget(clear_btn)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Departure", "Destination", "Departure Time", "End Time", "Active", "Actions"])

        root.addWidget(card)
        root.addLayout(actions)
        root.addWidget(self.table)
        self.refresh()

    def clear_form(self) -> None:
        self.editing_id = None
        self.save_btn.setText("Add Vehicle")
        self.nome.clear()
        self.departure.clear()
        self.destination.clear()

    def save(self) -> None:
        if not self.nome.text().strip():
            QMessageBox.warning(self, "Validation", "Vehicle name is required")
            return
        params = (
            self.nome.text().strip(),
            self.departure.text().strip(),
            self.destination.text().strip(),
            self.departure_time.currentText(),
            self.end_time.currentText(),
        )
        if self.editing_id is None:
            self.db.execute(
                "INSERT INTO veiculos (nome, departure, destination, departure_time, end_time, is_active) VALUES (?, ?, ?, ?, ?, 1)",
                params,
            )
        else:
            self.db.execute(
                "UPDATE veiculos SET nome=?, departure=?, destination=?, departure_time=?, end_time=? WHERE id=?",
                (*params, self.editing_id),
            )
        self.clear_form()
        self.refresh()

    def edit(self, vid: int) -> None:
        r = self.db.fetchone("SELECT * FROM veiculos WHERE id=?", (vid,))
        if not r:
            return
        self.editing_id = vid
        self.save_btn.setText("Update Vehicle")
        self.nome.setText(r["nome"])
        self.departure.setText(r["departure"] or "")
        self.destination.setText(r["destination"] or "")
        self.departure_time.setCurrentText(r["departure_time"] or "06:00")
        self.end_time.setCurrentText(r["end_time"] or "18:00")

    def toggle(self, vid: int) -> None:
        self.db.execute("UPDATE veiculos SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?", (vid,))
        self.refresh()

    def delete(self, vid: int) -> None:
        self.db.execute("DELETE FROM veiculos WHERE id=?", (vid,))
        self.refresh()

    def refresh(self) -> None:
        rows = self.db.fetchall("SELECT * FROM veiculos ORDER BY id DESC")
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(row["nome"]))
            self.table.setItem(i, 2, QTableWidgetItem(row["departure"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(row["destination"] or ""))
            self.table.setItem(i, 4, QTableWidgetItem(row["departure_time"] or ""))
            self.table.setItem(i, 5, QTableWidgetItem(row["end_time"] or ""))
            self.table.setItem(i, 6, QTableWidgetItem("Yes" if row["is_active"] else "No"))
            btns = QWidget()
            hl = QHBoxLayout(btns)
            hl.setContentsMargins(0, 0, 0, 0)
            b1 = QPushButton("Edit")
            b1.clicked.connect(lambda _=False, vid=row["id"]: self.edit(vid))
            b2 = QPushButton("Activate/Deactivate")
            b2.clicked.connect(lambda _=False, vid=row["id"]: self.toggle(vid))
            b3 = QPushButton("Delete")
            b3.clicked.connect(lambda _=False, vid=row["id"]: self.delete(vid))
            hl.addWidget(b1)
            hl.addWidget(b2)
            hl.addWidget(b3)
            self.table.setCellWidget(i, 7, btns)
