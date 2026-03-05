from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

from route_planner.database_manager import DatabaseManager
from route_planner.services.geocode_service import GeocodeService
from route_planner.services.map_service import MapService
from route_planner.services.matrix_service import MatrixService
from route_planner.services.solver_service import SolverService
from route_planner.ui.calcular_rotas_tab import CalcularRotasTab
from route_planner.ui.clientes_tab import ClientesTab
from route_planner.ui.mapa_tab import MapaTab
from route_planner.ui.presets_tab import PresetsTab
from route_planner.ui.veiculos_tab import VeiculosTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Planejador de Rotas - Lavanderia")
        self.resize(1200, 800)

        db = DatabaseManager()
        geocode = GeocodeService()
        matrix = MatrixService(db)
        solver = SolverService()
        map_service = MapService()

        tabs = QTabWidget()
        mapa_tab = MapaTab()

        tabs.addTab(ClientesTab(db, geocode), "Clientes")
        tabs.addTab(VeiculosTab(db), "Veículos")
        tabs.addTab(PresetsTab(db), "Presets")
        tabs.addTab(
            CalcularRotasTab(
                db,
                geocode,
                matrix,
                solver,
                map_service,
                on_map_ready=mapa_tab.load_map,
            ),
            "Calcular Rotas",
        )
        tabs.addTab(mapa_tab, "Mapa")

        self.setCentralWidget(tabs)
