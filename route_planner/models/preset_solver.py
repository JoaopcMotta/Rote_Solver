from dataclasses import dataclass


@dataclass
class PresetSolver:
    id: int | None
    nome: str
    tempo_limite_segundos: int = 30
    solucao_limite: int | None = None
    lns_tempo_limite: int | None = None
    first_solution_strategy: str = "PARALLEL_CHEAPEST_INSERTION"
    local_search_metaheuristic: str = "GUIDED_LOCAL_SEARCH"
    usar_relocate: bool = True
    usar_exchange: bool = True
    usar_2opt: bool = True
    usar_oropt: bool = True
    usar_cross: bool = False
    usar_lns: bool = True
    use_full_propagation: bool = True
    penalidade_cliente_nao_visitado: int = 10000
    tempo_parada_padrao_segundos: int = 600
    balancear_rotas: bool = False
