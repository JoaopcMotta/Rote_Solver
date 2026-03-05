"""Serviço para resolver VRP com OR-Tools."""

from __future__ import annotations

from dataclasses import dataclass

from ortools.constraint_solver import pywrapcp, routing_enums_pb2


@dataclass
class SolverResult:
    routes: list[dict]
    total_distance: int
    total_time: int
    dropped_nodes: list[int]


class SolverService:
    def solve(self, data: dict) -> SolverResult | None:
        manager = pywrapcp.RoutingIndexManager(
            len(data["time_matrix"]),
            len(data["starts"]),
            data["starts"],
            data["ends"],
        )
        routing = pywrapcp.RoutingModel(manager)

        def time_callback(from_index: int, to_index: int) -> int:
            f = manager.IndexToNode(from_index)
            t = manager.IndexToNode(to_index)
            base = data["time_matrix"][f][t]
            service = data["service_time"] if f in data["customer_node_indices"] else 0
            return base + service

        transit_cb = routing.RegisterTransitCallback(time_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_cb)

        routing.AddDimension(transit_cb, 3600, 24 * 3600, False, "Time")
        time_dimension = routing.GetDimensionOrDie("Time")

        for node_idx, tw in data["time_windows"].items():
            time_dimension.CumulVar(manager.NodeToIndex(node_idx)).SetRange(tw[0], tw[1])

        for vehicle_id, start_time in enumerate(data["vehicle_start_times"]):
            start_index = routing.Start(vehicle_id)
            time_dimension.CumulVar(start_index).SetRange(start_time, 24 * 3600)
            if "vehicle_end_times" in data:
                end_index = routing.End(vehicle_id)
                time_dimension.CumulVar(end_index).SetRange(0, data["vehicle_end_times"][vehicle_id])

        for node in data["customer_node_indices"]:
            routing.AddDisjunction([manager.NodeToIndex(node)], int(data["penalty"]))

        if data.get("balance_routes"):
            distance_cb = routing.RegisterTransitCallback(
                lambda i, j: data["distance_matrix"][manager.IndexToNode(i)][manager.IndexToNode(j)]
            )
            routing.AddDimension(distance_cb, 0, 10**9, True, "Distance")
            routing.GetDimensionOrDie("Distance").SetGlobalSpanCostCoefficient(100)

        params = pywrapcp.DefaultRoutingSearchParameters()
        params.first_solution_strategy = getattr(routing_enums_pb2.FirstSolutionStrategy, data["first_solution_strategy"])
        params.local_search_metaheuristic = getattr(
            routing_enums_pb2.LocalSearchMetaheuristic, data["local_search_metaheuristic"]
        )
        params.time_limit.seconds = int(data["time_limit"])
        params.use_full_propagation = bool(data.get("use_full_propagation", True))
        if data.get("solution_limit"):
            params.solution_limit = int(data["solution_limit"])
        params.log_search = bool(data.get("log_search", False))

        solution = routing.SolveWithParameters(params)
        if not solution:
            return None

        routes: list[dict] = []
        total_distance = 0
        total_time = 0
        for vehicle_id in range(len(data["starts"])):
            index = routing.Start(vehicle_id)
            route_nodes = []
            route_distance = 0
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                arrival = solution.Value(time_dimension.CumulVar(index))
                route_nodes.append({"node": node, "arrival": arrival})
                prev = index
                index = solution.Value(routing.NextVar(index))
                route_distance += data["distance_matrix"][manager.IndexToNode(prev)][manager.IndexToNode(index)]
            route_nodes.append({"node": manager.IndexToNode(index), "arrival": solution.Value(time_dimension.CumulVar(index))})
            routes.append({"vehicle": vehicle_id, "nodes": route_nodes, "distance": route_distance})
            total_distance += route_distance
            total_time += route_nodes[-1]["arrival"]

        dropped = []
        for node in data["customer_node_indices"]:
            if solution.Value(routing.NextVar(manager.NodeToIndex(node))) == manager.NodeToIndex(node):
                dropped.append(node)

        return SolverResult(routes=routes, total_distance=total_distance, total_time=total_time, dropped_nodes=dropped)
