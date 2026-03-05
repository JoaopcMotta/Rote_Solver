from dataclasses import dataclass


@dataclass
class Cliente:
    id: int | None
    nome: str
    endereco: str
    latitude: float | None = None
    longitude: float | None = None
    ativo: bool = True
    segunda: bool = True
    terca: bool = True
    quarta: bool = True
    quinta: bool = True
    sexta: bool = True
    sabado: bool = False
    hora_inicio: str | None = None
    hora_fim: str | None = None
    periodo: str | None = None
