from __future__ import annotations

import json

from PySide6.QtWidgets import QMessageBox, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from route_planner.database_manager import DatabaseManager
from route_planner.services.map_service import MapService
from route_planner.ui.route_map_dialog import RouteMapDialog


class RoutesHistoryTab(QWidget):
    def __init__(self, db: DatabaseManager, map_service: MapService) -> None:
        super().__init__()
        self.db = db
        self.map_service = map_service
        self.last_dialog = None

        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Date",
            "Weekday",
            "Preset Used",
            "Vehicles Used",
            "Total Distance",
            "Total Time",
            "Actions",
        ])
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        rows = self.db.fetchall(
            """
            SELECT r.*, p.preset_name
            FROM rotas_calculadas r
            LEFT JOIN presets_solver p ON p.id = r.preset_id
            ORDER BY r.id DESC
            """
        )
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["data_calculo"][:19]))
            self.table.setItem(i, 1, QTableWidgetItem(r["dia_semana"]))
            self.table.setItem(i, 2, QTableWidgetItem(r["preset_name"] or "-"))
            self.table.setItem(i, 3, QTableWidgetItem(r["vehicles_used"] or ""))
            self.table.setItem(i, 4, QTableWidgetItem(f"{r['distancia_total']/1000:.2f} km"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{int(r['tempo_total'])//3600}h{int(r['tempo_total'])%3600//60:02d}"))

            act = QWidget()
            hl = QHBoxLayout(act)
            hl.setContentsMargins(0, 0, 0, 0)
            b_details = QPushButton("View Details")
            b_details.clicked.connect(lambda _=False, row=r: self.view_details(row))
            b_map = QPushButton("View Map")
            b_map.clicked.connect(lambda _=False, row=r: self.view_map(row))
            b_export = QPushButton("Export")
            b_export.clicked.connect(lambda _=False, row=r: self.export_route(row))
            b_del = QPushButton("Delete")
            b_del.clicked.connect(lambda _=False, rid=r["id"]: self.delete_route(rid))
            hl.addWidget(b_details)
            hl.addWidget(b_map)
            hl.addWidget(b_export)
            hl.addWidget(b_del)
            self.table.setCellWidget(i, 6, act)

    def view_details(self, row) -> None:
        QMessageBox.information(self, "Route Details", row["route_summary"] or "No details available")

    def view_map(self, row) -> None:
        payload = row["map_payload"]
        if not payload:
            return
        data = json.loads(payload)
        html = self.map_service.generate_map(tuple(data["center"]), data["routes"], "route_map_history.html")
        self.last_dialog = RouteMapDialog(html, data["google_link"], self)
        self.last_dialog.show()

    def export_route(self, row) -> None:
        with open(f"route_{row['id']}.txt", "w", encoding="utf-8") as f:
            f.write(row["route_summary"] or "")

    def delete_route(self, route_id: int) -> None:
        self.db.execute("DELETE FROM rota_paradas WHERE rota_id=?", (route_id,))
        self.db.execute("DELETE FROM rotas_calculadas WHERE id=?", (route_id,))
        self.refresh()
