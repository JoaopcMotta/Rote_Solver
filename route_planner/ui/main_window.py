from __future__ import annotations

from PySide6.QtWidgets import QAbstractItemView, QFrame, QHBoxLayout, QListWidget, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

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
from route_planner.ui.i18n import i18n


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Planejador de Rotas - Lavanderia")
        self.resize(1300, 820)

        db = DatabaseManager()
        geocode = GeocodeService()
        matrix = MatrixService(db)
        solver = SolverService()
        map_service = MapService()

        central = QWidget()
        layout = QHBoxLayout(central)

        sidebar = QListWidget()
        sidebar.addItems([i18n.t("clients","Clientes"), i18n.t("vehicles","Veículos"), i18n.t("presets","Presets"), i18n.t("calculate_routes","Calcular Rotas"), i18n.t("routes_history","Histórico de Rotas")])
        sidebar.setFixedWidth(240)
        sidebar.setSelectionMode(QAbstractItemView.SingleSelection)

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
            QMainWindow { background: #F5F6FA; color:#2C3E50; }
            QFrame#Card, QFrame { background: #FFFFFF; border: 1px solid #E2E6EF; border-radius: 10px; color:#2C3E50; }
            QListWidget { background: #FFFFFF; color: #2C3E50; border: 1px solid #E2E6EF; border-radius: 10px; padding: 8px; font-size: 13px; }
            QListWidget::item { padding: 10px; border-radius: 8px; }
            QListWidget::item:selected { background: #4A90E2; color: white; }
            QLabel { color:#2C3E50; font-size: 13px; }
            QPushButton { background: #4A90E2; color: white; border: none; border-radius: 8px; padding: 8px 12px; }
            QPushButton:hover { background: #3b7fcc; }
            QLineEdit, QComboBox, QTextEdit, QTableWidget, QListWidget { border: 1px solid #D5DCE8; border-radius: 8px; padding: 6px; color:#2C3E50; background:#FFFFFF; }
            QHeaderView::section { background:#F0F3F8; color:#2C3E50; padding:6px; border:none; font-size:12px; }
            QTableWidget { alternate-background-color: #F8FAFD; gridline-color:#E6EBF2; }
            QTableWidget::item:hover { background: #EAF2FE; }
            """
        )
