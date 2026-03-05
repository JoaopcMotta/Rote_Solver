from dataclasses import dataclass


@dataclass
class Veiculo:
    id: int | None
    nome: str
    endereco_inicio: str
    endereco_fim: str
    hora_inicio: str
    hora_fim: str
    capacidade: int
    ativo: bool = True
