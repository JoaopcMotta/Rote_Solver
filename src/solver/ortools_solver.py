"""OR-Tools VRP solver that consumes in-memory distance/time matrices."""

from __future__ import annotations

from dataclasses import dataclass

from ortools.constraint_solver import pywrapcp, routing_enums_pb2


@dataclass
class RouteSolution:
    routes: list[dict]
    total_distance: int
    total_duration: int
    dropped_nodes: list[int]


class OrtoolsSolver:
    def solve(self, data: dict) -> RouteSolution | None:
        manager = pywrapcp.RoutingIndexManager(
            len(data["duration_matrix"]),
            len(data["starts"]),
            data["starts"],
            data["ends"],
        )
        routing = pywrapcp.RoutingModel(manager)

        def transit_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data["duration_matrix"][from_node][to_node]

        transit_idx = routing.RegisterTransitCallback(transit_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

        routing.AddDimension(transit_idx, 0, int(data.get("max_route_duration", 24 * 3600)), True, "Time")

        for node in data.get("customer_nodes", []):
            routing.AddDisjunction([manager.NodeToIndex(node)], int(data["unserved_penalty"]))

        params = pywrapcp.DefaultRoutingSearchParameters()
        params.first_solution_strategy = getattr(
            routing_enums_pb2.FirstSolutionStrategy,
            data.get("first_solution_strategy", "PARALLEL_CHEAPEST_INSERTION"),
        )
        params.local_search_metaheuristic = getattr(
            routing_enums_pb2.LocalSearchMetaheuristic,
            data.get("local_search_metaheuristic", "GUIDED_LOCAL_SEARCH"),
        )
        params.time_limit.seconds = int(data.get("time_limit_seconds", 30))

        solution = routing.SolveWithParameters(params)
        if not solution:
            return None

        routes: list[dict] = []
        total_distance = 0
        total_duration = 0

        for vehicle_id in range(len(data["starts"])):
            idx = routing.Start(vehicle_id)
            nodes: list[int] = []
            route_cost = 0
            while not routing.IsEnd(idx):
                n = manager.IndexToNode(idx)
                nodes.append(n)
                prev = idx
                idx = solution.Value(routing.NextVar(idx))
                route_cost += data["distance_matrix"][manager.IndexToNode(prev)][manager.IndexToNode(idx)]
            nodes.append(manager.IndexToNode(idx))
            routes.append({"vehicle": vehicle_id, "nodes": nodes, "distance": route_cost})
            total_distance += route_cost
            total_duration += route_cost

        dropped = []
        for node in data.get("customer_nodes", []):
            if solution.Value(routing.NextVar(manager.NodeToIndex(node))) == manager.NodeToIndex(node):
                dropped.append(node)

        return RouteSolution(routes, total_distance, total_duration, dropped)
