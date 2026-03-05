from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from route_planner.database_manager import DatabaseManager
from route_planner.services.geocode_service import GeocodeService
from route_planner.services.map_service import MapService
from route_planner.services.matrix_service import MatrixService
from route_planner.services.solver_service import SolverService


WEEKDAY_FIELD = {
    "segunda": "segunda",
    "terca": "terca",
    "quarta": "quarta",
    "quinta": "quinta",
    "sexta": "sexta",
    "sabado": "sabado",
}


class CalcularRotasTab(QWidget):
    def __init__(
        self,
        db: DatabaseManager,
        geocode: GeocodeService,
        matrix: MatrixService,
        solver: SolverService,
        map_service: MapService,
        on_map_ready,
    ) -> None:
        super().__init__()
        self.db = db
        self.geocode = geocode
        self.matrix = matrix
        self.solver = solver
        self.map_service = map_service
        self.on_map_ready = on_map_ready

        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.day_combo = QComboBox()
        self.day_combo.addItems(["segunda", "terca", "quarta", "quinta", "sexta", "sabado"])
        self.preset_combo = QComboBox()
        self.refresh_presets()

        calc_btn = QPushButton("Calcular rota")
        calc_btn.clicked.connect(self.calculate)

        controls.addWidget(QLabel("Dia"))
        controls.addWidget(self.day_combo)
        controls.addWidget(QLabel("Preset"))
        controls.addWidget(self.preset_combo)
        controls.addWidget(calc_btn)

        self.output = QTextEdit()
        self.output.setReadOnly(True)

        layout.addLayout(controls)
        layout.addWidget(self.output)

    def refresh_presets(self) -> None:
        self.preset_combo.clear()
        for row in self.db.fetchall("SELECT id, nome FROM presets_solver ORDER BY id"):
            self.preset_combo.addItem(row["nome"], row["id"])

    @staticmethod
    def hhmm_to_sec(value: str | None, default: int = 0) -> int:
        if not value:
            return default
        h, m = value.split(":")
        return int(h) * 3600 + int(m) * 60

    def _fetch_nodes(self, day: str):
        clients = self.db.fetchall(
            f"SELECT * FROM clientes WHERE ativo = 1 AND {WEEKDAY_FIELD[day]} = 1 AND latitude IS NOT NULL AND longitude IS NOT NULL"
        )
        vehicles = self.db.fetchall("SELECT * FROM veiculos WHERE ativo = 1")
        if not clients or not vehicles:
            return None, None

        points = []
        starts, ends, vehicle_start_times = [], [], []

        for v in vehicles:
            s = self.geocode.geocode(v["endereco_inicio"])
            e = self.geocode.geocode(v["endereco_fim"])
            if not s or not e:
                continue
            s_idx = len(points)
            points.append({"uid": f"v{v['id']}_s", "coord": s, "label": v["endereco_inicio"], "type": "start"})
            e_idx = len(points)
            points.append({"uid": f"v{v['id']}_e", "coord": e, "label": v["endereco_fim"], "type": "end"})
            starts.append(s_idx)
            ends.append(e_idx)
            vehicle_start_times.append(self.hhmm_to_sec(v["hora_inicio"], 7 * 3600))

        customer_indices = []
        time_windows = {}
        for c in clients:
            idx = len(points)
            points.append(
                {
                    "uid": f"c{c['id']}",
                    "coord": (c["latitude"], c["longitude"]),
                    "label": c["nome"],
                    "type": "customer",
                    "id": c["id"],
                }
            )
            customer_indices.append(idx)
            time_windows[idx] = (
                self.hhmm_to_sec(c["hora_inicio"], 8 * 3600),
                self.hhmm_to_sec(c["hora_fim"], 18 * 3600),
            )

        return {
            "points": points,
            "starts": starts,
            "ends": ends,
            "customer_indices": customer_indices,
            "time_windows": time_windows,
            "vehicles": vehicles,
            "vehicle_start_times": vehicle_start_times,
        }, clients

    def calculate(self) -> None:
        day = self.day_combo.currentText()
        preset_id = self.preset_combo.currentData()
        preset = self.db.fetchone("SELECT * FROM presets_solver WHERE id = ?", (preset_id,))

        data, clients = self._fetch_nodes(day)
        if not data:
            QMessageBox.warning(self, "Dados", "Cadastre clientes geocodificados e veículos ativos.")
            return

        dist, times = self.matrix.build_square_matrix(data["points"])
        solver_data = {
            "distance_matrix": dist,
            "time_matrix": times,
            "starts": data["starts"],
            "ends": data["ends"],
            "customer_node_indices": data["customer_indices"],
            "time_windows": data["time_windows"],
            "vehicle_start_times": data["vehicle_start_times"],
            "service_time": int(preset["tempo_parada_padrao_segundos"]),
            "penalty": int(preset["penalidade_cliente_nao_visitado"]),
            "balance_routes": bool(preset["balancear_rotas"]),
            "time_limit": int(preset["tempo_limite_segundos"]),
            "first_solution_strategy": preset["first_solution_strategy"],
            "local_search_metaheuristic": preset["local_search_metaheuristic"],
            "use_full_propagation": bool(preset["use_full_propagation"]),
        }

        result = self.solver.solve(solver_data)
        if not result:
            self.output.setPlainText("Não foi possível encontrar solução.")
            return

        lines = []
        map_lines = []
        for route in result.routes:
            lines.append(f"CARRO {route['vehicle'] + 1}")
            points = []
            for stop in route["nodes"]:
                p = data["points"][stop["node"]]
                hh = stop["arrival"] // 3600
                mm = (stop["arrival"] % 3600) // 60
                lines.append(f"→ {p['label']} ({hh:02d}:{mm:02d})")
                points.append(p["coord"])
            lines.append(f"Distância total: {route['distance'] / 1000:.1f} km\n")
            map_lines.append({"name": f"Veículo {route['vehicle'] + 1}", "coords": points})

        not_served = len(result.dropped_nodes)
        served = len(clients) - not_served
        lines.append(f"Distância total global: {result.total_distance / 1000:.2f} km")
        lines.append(f"Tempo total global: {result.total_time // 3600}h{(result.total_time % 3600) // 60:02d}")
        lines.append(f"Clientes atendidos: {served}")
        lines.append(f"Clientes não atendidos: {not_served}")
        self.output.setPlainText("\n".join(lines))

        route_id = self.db.execute(
            "INSERT INTO rotas_calculadas (data_calculo, dia_semana, preset_id, distancia_total, tempo_total) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), day, preset_id, result.total_distance, result.total_time),
        ).lastrowid

        for route in result.routes:
            for order, stop in enumerate(route["nodes"]):
                point = data["points"][stop["node"]]
                cliente_id = point.get("id")
                self.db.execute(
                    "INSERT INTO rota_paradas (rota_id, veiculo_id, ordem, cliente_id, tempo_chegada, distancia_acumulada) VALUES (?, ?, ?, ?, ?, ?)",
                    (route_id, route["vehicle"] + 1, order, cliente_id, str(stop["arrival"]), route["distance"]),
                )

        center = map_lines[0]["coords"][0]
        html = self.map_service.generate_map(center, map_lines, "route_map.html")
        google_points = []
        for route in result.routes:
            for stop in route["nodes"]:
                google_points.append(data["points"][stop["node"]]["label"])
        self.on_map_ready(html, self.map_service.google_maps_link(google_points))
