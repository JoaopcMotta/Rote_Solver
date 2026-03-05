from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from route_planner.database_manager import DatabaseManager


class PresetsTab(QWidget):
    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        self.db = db
        self.editing_id: int | None = None

        root = QVBoxLayout(self)
        card = QFrame()
        form = QFormLayout(card)
        self.name = QLineEdit()
        self.time_limit = QComboBox()
        self.stop_min = QComboBox()
        self.penalty = QLineEdit("10000")
        for v in [10, 20, 30, 45, 60, 90, 120]:
            self.time_limit.addItem(str(v))
        for v in [5, 10, 15, 20, 30]:
            self.stop_min.addItem(str(v))

        self.first_solution = QComboBox()
        self.first_solution.addItems(["PATH_CHEAPEST_ARC", "PARALLEL_CHEAPEST_INSERTION", "SAVINGS", "AUTOMATIC"])
        self.meta = QComboBox()
        self.meta.addItems(["GUIDED_LOCAL_SEARCH", "TABU_SEARCH", "SIMULATED_ANNEALING", "AUTOMATIC"])
        self.solution_limit = QComboBox()
        self.solution_limit.addItems(["", "100", "500", "1000", "5000"])
        self.log_search = QCheckBox("Log Search")
        self.full_prop = QCheckBox("Use Full Propagation")
        self.full_prop.setChecked(True)

        form.addRow("Preset Name", self.name)
        form.addRow("Time Limit (seconds)", self.time_limit)
        form.addRow("Stop Time (minutes)", self.stop_min)
        form.addRow("Penalty Value", self.penalty)
        form.addRow("First Solution Strategy", self.first_solution)
        form.addRow("Local Search Metaheuristic", self.meta)
        form.addRow("Solution Limit", self.solution_limit)
        form.addRow(self.log_search)
        form.addRow(self.full_prop)

        actions = QHBoxLayout()
        self.save_btn = QPushButton("Add Preset")
        self.save_btn.clicked.connect(self.save)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear)
        actions.addWidget(self.save_btn)
        actions.addWidget(clear_btn)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["ID", "Preset", "Time", "Strategy", "Meta", "Penalty", "Actions"])

        root.addWidget(card)
        root.addLayout(actions)
        root.addWidget(self.table)
        self.refresh()

    def clear(self) -> None:
        self.editing_id = None
        self.save_btn.setText("Add Preset")
        self.name.clear()

    def save(self) -> None:
        sol_lim = self.solution_limit.currentText().strip() or None
        params = (
            self.name.text().strip(),
            int(self.time_limit.currentText()),
            int(self.stop_min.currentText()),
            int(self.penalty.text() or 10000),
            self.first_solution.currentText(),
            self.meta.currentText(),
            int(sol_lim) if sol_lim else None,
            1 if self.log_search.isChecked() else 0,
            1 if self.full_prop.isChecked() else 0,
        )
        if self.editing_id is None:
            self.db.execute(
                """
                INSERT INTO presets_solver(
                    preset_name,time_limit_seconds,stop_time_minutes,penalty_value,
                    first_solution_strategy,local_search_metaheuristic,solution_limit,log_search,use_full_propagation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params,
            )
        else:
            self.db.execute(
                """
                UPDATE presets_solver SET
                    preset_name=?,time_limit_seconds=?,stop_time_minutes=?,penalty_value=?,
                    first_solution_strategy=?,local_search_metaheuristic=?,solution_limit=?,log_search=?,use_full_propagation=?
                WHERE id=?
                """,
                (*params, self.editing_id),
            )
        self.clear()
        self.refresh()

    def edit(self, pid: int) -> None:
        r = self.db.fetchone("SELECT * FROM presets_solver WHERE id=?", (pid,))
        if not r:
            return
        self.editing_id = pid
        self.save_btn.setText("Update Preset")
        self.name.setText(r["preset_name"])
        self.time_limit.setCurrentText(str(r["time_limit_seconds"]))
        self.stop_min.setCurrentText(str(r["stop_time_minutes"]))
        self.penalty.setText(str(r["penalty_value"]))
        self.first_solution.setCurrentText(r["first_solution_strategy"])
        self.meta.setCurrentText(r["local_search_metaheuristic"])
        self.solution_limit.setCurrentText(str(r["solution_limit"] or ""))
        self.log_search.setChecked(bool(r["log_search"]))
        self.full_prop.setChecked(bool(r["use_full_propagation"]))

    def delete(self, pid: int) -> None:
        self.db.execute("DELETE FROM presets_solver WHERE id=?", (pid,))
        self.refresh()

    def refresh(self) -> None:
        rows = self.db.fetchall("SELECT * FROM presets_solver ORDER BY id")
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(r["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(r["preset_name"]))
            self.table.setItem(i, 2, QTableWidgetItem(str(r["time_limit_seconds"])))
            self.table.setItem(i, 3, QTableWidgetItem(r["first_solution_strategy"]))
            self.table.setItem(i, 4, QTableWidgetItem(r["local_search_metaheuristic"]))
            self.table.setItem(i, 5, QTableWidgetItem(str(r["penalty_value"])))
            w = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            b1 = QPushButton("Edit")
            b1.clicked.connect(lambda _=False, pid=r["id"]: self.edit(pid))
            b2 = QPushButton("Delete")
            b2.clicked.connect(lambda _=False, pid=r["id"]: self.delete(pid))
            hl.addWidget(b1)
            hl.addWidget(b2)
            self.table.setCellWidget(i, 6, w)
