"""Serviços para geração de mapa e links de navegação."""

from __future__ import annotations

import folium


class MapService:
    COLORS = ["red", "blue", "green", "purple", "orange", "darkred", "cadetblue", "black"]

    def generate_map(self, center: tuple[float, float], route_lines: list[dict], output_file: str) -> str:
        m = folium.Map(location=center, zoom_start=12)

        for i, route in enumerate(route_lines):
            color = self.COLORS[i % len(self.COLORS)]
            folium.PolyLine(route["coords"], color=color, weight=5, opacity=0.8).add_to(m)
            for idx, point in enumerate(route["coords"]):
                folium.Marker(point, tooltip=f"{route['name']} #{idx}").add_to(m)

        m.save(output_file)
        return output_file

    @staticmethod
    def google_maps_link(points: list[str]) -> str:
        path = "/".join(p.replace(" ", "+") for p in points)
        return f"https://www.google.com/maps/dir/{path}"
