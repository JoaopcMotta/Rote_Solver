from dataclasses import dataclass, field


@dataclass
class ParadaRota:
    veiculo_id: int
    ordem: int
    cliente_id: int | None
    tempo_chegada: str | None
    distancia_acumulada: float


@dataclass
class RotaCalculada:
    id: int | None
    data_calculo: str
    dia_semana: str
    preset_id: int
    distancia_total: float
    tempo_total: float
    paradas: list[ParadaRota] = field(default_factory=list)
