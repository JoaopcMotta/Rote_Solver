from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QListWidget, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from route_planner.database_manager import DatabaseManager
from route_planner.services.geocode_service import GeocodeService
from route_planner.services.map_service import MapService
from route_planner.services.matrix_service import MatrixService
from route_planner.services.solver_service import SolverService
from route_planner.ui.calcular_rotas_tab import CalcularRotasTab
from route_planner.ui.clientes_tab import ClientesTab
from route_planner.ui.presets_tab import PresetsTab
from route_planner.ui.routes_history_tab import RoutesHistoryTab
from route_planner.ui.veiculos_tab import VeiculosTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Route Planner - Laundry")
        self.resize(1300, 820)

        db = DatabaseManager()
        geocode = GeocodeService()
        matrix = MatrixService(db)
        solver = SolverService()
        map_service = MapService()

        central = QWidget()
        layout = QHBoxLayout(central)

        sidebar = QListWidget()
        sidebar.addItems(["Clients", "Vehicles", "Presets", "Calculate Routes", "Routes History"])
        sidebar.setFixedWidth(220)

        stack = QStackedWidget()
        history = RoutesHistoryTab(db, map_service)
        stack.addWidget(ClientesTab(db, geocode))
        stack.addWidget(VeiculosTab(db))
        stack.addWidget(PresetsTab(db))
        stack.addWidget(CalcularRotasTab(db, geocode, matrix, solver, map_service, on_saved=history.refresh))
        stack.addWidget(history)

        sidebar.currentRowChanged.connect(stack.setCurrentIndex)
        sidebar.setCurrentRow(0)

        side_frame = QFrame()
        side_layout = QVBoxLayout(side_frame)
        side_layout.addWidget(sidebar)

        content = QFrame()
        content_layout = QVBoxLayout(content)
        content_layout.addWidget(stack)

        layout.addWidget(side_frame)
        layout.addWidget(content, 1)
        self.setCentralWidget(central)

        self.setStyleSheet(
            """
            QMainWindow { background: #f3f5f9; }
            QFrame#Card, QFrame { background: white; border: 1px solid #e3e7ef; border-radius: 10px; }
            QListWidget { background: #1f2937; color: #e5e7eb; border-radius: 10px; padding: 8px; font-size: 13px; }
            QListWidget::item { padding: 10px; border-radius: 8px; }
            QListWidget::item:selected { background: #3b82f6; }
            QPushButton { background: #3b82f6; color: white; border: none; border-radius: 8px; padding: 8px 12px; }
            QPushButton:hover { background: #2563eb; }
            QLineEdit, QComboBox, QTextEdit, QTableWidget { border: 1px solid #d0d7e2; border-radius: 8px; padding: 6px; }
            """
        )
