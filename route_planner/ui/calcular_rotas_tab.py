from __future__ import annotations

import json
from datetime import datetime

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from route_planner.database_manager import DatabaseManager
from route_planner.services.geocode_service import GeocodeService
from route_planner.services.map_service import MapService
from route_planner.services.matrix_service import MatrixService
from route_planner.services.solver_service import SolverService
from route_planner.ui.route_map_dialog import RouteMapDialog

WEEKDAY_FIELD = {
    "Monday": "collect_monday",
    "Tuesday": "collect_tuesday",
    "Wednesday": "collect_wednesday",
    "Thursday": "collect_thursday",
    "Friday": "collect_friday",
    "Saturday": "collect_saturday",
    "Sunday": "collect_sunday",
}


class CalcularRotasTab(QWidget):
    def __init__(self, db: DatabaseManager, geocode: GeocodeService, matrix: MatrixService, solver: SolverService, map_service: MapService, on_saved=None) -> None:
        super().__init__()
        self.db = db
        self.geocode = geocode
        self.matrix = matrix
        self.solver = solver
        self.map_service = map_service
        self.on_saved = on_saved
        self.last_map = None

        root = QVBoxLayout(self)
        card = QFrame()
        ctl = QHBoxLayout(card)

        self.day_combo = QComboBox()
        self.day_combo.addItems(list(WEEKDAY_FIELD.keys()))
        self.preset_combo = QComboBox()
        self.refresh_presets()

        self.vehicles_list = QListWidget()
        self.vehicles_list.setMaximumHeight(110)
        self.refresh_vehicles()

        calc_btn = QPushButton("Calculate Route")
        calc_btn.clicked.connect(self.calculate)
        map_btn = QPushButton("View Route Map")
        map_btn.clicked.connect(self.open_map)

        ctl.addWidget(QLabel("Weekday"))
        ctl.addWidget(self.day_combo)
        ctl.addWidget(QLabel("Preset"))
        ctl.addWidget(self.preset_combo)
        ctl.addWidget(QLabel("Vehicles"))
        ctl.addWidget(self.vehicles_list)
        ctl.addWidget(calc_btn)
        ctl.addWidget(map_btn)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        root.addWidget(card)
        root.addWidget(self.output)

    def refresh_presets(self) -> None:
        self.preset_combo.clear()
        for r in self.db.fetchall("SELECT id, preset_name FROM presets_solver ORDER BY id"):
            self.preset_combo.addItem(r["preset_name"], r["id"])

    def refresh_vehicles(self) -> None:
        self.vehicles_list.clear()
        for v in self.db.fetchall("SELECT id, nome FROM veiculos WHERE is_active=1 ORDER BY nome"):
            item = QListWidgetItem(v["nome"])
            item.setData(Qt.UserRole, v["id"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.vehicles_list.addItem(item)

    @staticmethod
    def hhmm_to_sec(value: str | None, default: int = 0) -> int:
        if not value:
            return default
        h, m = value.split(":")
        return int(h) * 3600 + int(m) * 60

    def selected_vehicle_ids(self) -> list[int]:
        ids = []
        for i in range(self.vehicles_list.count()):
            item = self.vehicles_list.item(i)
            if item.checkState() == Qt.Checked:
                ids.append(item.data(Qt.UserRole))
        return ids

    def calculate(self) -> None:
        day = self.day_combo.currentText()
        preset_id = self.preset_combo.currentData()
        vehicle_ids = self.selected_vehicle_ids()
        if not vehicle_ids:
            QMessageBox.warning(self, "Validation", "Select at least one vehicle.")
            return

        clients = self.db.fetchall(
            f"SELECT * FROM clientes WHERE is_active=1 AND {WEEKDAY_FIELD[day]}=1 AND latitude IS NOT NULL AND longitude IS NOT NULL"
        )
        if not clients:
            QMessageBox.warning(self, "Data", "No active geocoded clients for selected weekday.")
            return

        vehicles = self.db.fetchall(
            f"SELECT * FROM veiculos WHERE id IN ({','.join('?' for _ in vehicle_ids)})",
            vehicle_ids,
        )
        points, starts, ends, vehicle_start_times = [], [], [], []
        vehicle_names = []
        for v in vehicles:
            s = self.geocode.geocode(v["departure"]) or self.geocode.geocode(v["departure"])
            e = self.geocode.geocode(v["destination"]) or self.geocode.geocode(v["destination"])
            if not s or not e:
                continue
            starts.append(len(points))
            points.append({"uid": f"v{v['id']}_s", "coord": s, "label": v["departure"], "type": "start"})
            ends.append(len(points))
            points.append({"uid": f"v{v['id']}_e", "coord": e, "label": v["destination"], "type": "end"})
            vehicle_start_times.append(self.hhmm_to_sec(v["departure_time"], 6 * 3600))
            vehicle_names.append(v["nome"])

        customer_indices, windows = [], {}
        for c in clients:
            idx = len(points)
            points.append({"uid": f"c{c['id']}", "coord": (c["latitude"], c["longitude"]), "label": c["nome"], "id": c["id"], "type": "customer"})
            customer_indices.append(idx)
            windows[idx] = (self.hhmm_to_sec(c["window_start"], 8 * 3600), self.hhmm_to_sec(c["window_end"], 18 * 3600))

        preset = self.db.fetchone("SELECT * FROM presets_solver WHERE id=?", (preset_id,))
        dist, times = self.matrix.build_square_matrix(points)
        result = self.solver.solve(
            {
                "distance_matrix": dist,
                "time_matrix": times,
                "starts": starts,
                "ends": ends,
                "customer_node_indices": customer_indices,
                "time_windows": windows,
                "vehicle_start_times": vehicle_start_times,
                "service_time": int(preset["stop_time_minutes"]) * 60,
                "penalty": int(preset["penalty_value"]),
                "time_limit": int(preset["time_limit_seconds"]),
                "first_solution_strategy": preset["first_solution_strategy"],
                "local_search_metaheuristic": preset["local_search_metaheuristic"],
                "use_full_propagation": bool(preset["use_full_propagation"]),
            }
        )
        if not result:
            self.output.setPlainText("No solution found")
            return

        lines, map_lines = [], []
        for route in result.routes:
            lines.append(f"VEHICLE {route['vehicle'] + 1}")
            coords, labels = [], []
            for stop in route["nodes"]:
                p = points[stop["node"]]
                hh = stop["arrival"] // 3600
                mm = (stop["arrival"] % 3600) // 60
                lines.append(f"→ {p['label']} ({hh:02d}:{mm:02d})")
                coords.append(p["coord"])
                labels.append(p["label"])
            lines.append(f"Distance: {route['distance']/1000:.1f} km\n")
            map_lines.append({"name": f"Vehicle {route['vehicle'] + 1}", "coords": coords})

        lines.append(f"Global Distance: {result.total_distance/1000:.2f} km")
        lines.append(f"Global Time: {result.total_time//3600}h{(result.total_time%3600)//60:02d}")
        lines.append(f"Served Clients: {len(clients)-len(result.dropped_nodes)}")
        lines.append(f"Unserved Clients: {len(result.dropped_nodes)}")
        summary = "\n".join(lines)
        self.output.setPlainText(summary)

        center = map_lines[0]["coords"][0]
        html = self.map_service.generate_map(center, map_lines, "route_map.html")
        google_points = [points[s["node"]]["label"] for r in result.routes for s in r["nodes"]]
        google_link = self.map_service.google_maps_link(google_points)
        self.last_map = (html, google_link)

        map_payload = json.dumps({"center": center, "routes": map_lines, "google_link": google_link})
        route_id = self.db.execute(
            """
            INSERT INTO rotas_calculadas(data_calculo,dia_semana,preset_id,vehicles_used,route_summary,map_payload,distancia_total,tempo_total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (datetime.now().isoformat(), day, preset_id, ", ".join(vehicle_names), summary, map_payload, result.total_distance, result.total_time),
        ).lastrowid

        for route in result.routes:
            for order, stop in enumerate(route["nodes"]):
                point = points[stop["node"]]
                self.db.execute(
                    "INSERT INTO rota_paradas(rota_id,veiculo_id,ordem,cliente_id,tempo_chegada,distancia_acumulada) VALUES (?, ?, ?, ?, ?, ?)",
                    (route_id, route["vehicle"] + 1, order, point.get("id"), str(stop["arrival"]), route["distance"]),
                )
        if self.on_saved:
            self.on_saved()

    def open_map(self) -> None:
        if not self.last_map:
            return
        dialog = RouteMapDialog(self.last_map[0], self.last_map[1], self)
        dialog.exec()
