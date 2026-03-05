from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView


class MapaTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.web = QWebEngineView()
        self.btn_google = QPushButton("Abrir no Google Maps")
        self.google_link = ""

        layout = QVBoxLayout(self)
        layout.addWidget(self.web)
        layout.addWidget(self.btn_google)
        self.btn_google.clicked.connect(self.open_google)

    def load_map(self, html_file: str, google_link: str) -> None:
        self.google_link = google_link
        self.web.load(QUrl.fromLocalFile(str(Path(html_file).resolve())))

    def open_google(self) -> None:
        if self.google_link:
            self.web.load(QUrl(self.google_link))
