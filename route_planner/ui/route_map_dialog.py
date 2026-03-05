from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QPushButton, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView


class RouteMapDialog(QDialog):
    def __init__(self, html_file: str, google_link: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Route Map")
        self.resize(900, 650)
        self.google_link = google_link
        self.web = QWebEngineView()
        self.web.load(QUrl.fromLocalFile(str(Path(html_file).resolve())))
        btn = QPushButton("Open in Google Maps")
        btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.google_link)))
        layout = QVBoxLayout(self)
        layout.addWidget(self.web)
        layout.addWidget(btn)
