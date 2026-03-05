# Route Planner - Lavanderia Industrial

## Executar em desenvolvimento

```bash
python -m route_planner.main
```

## Gerar executável Windows

```bash
pyinstaller --onefile --noconsole main.py
```

## Interface

- Sidebar moderna com páginas: Clients, Vehicles, Presets, Calculate Routes e Routes History.
- Mapa aberto sob demanda em nova janela após cálculo.

## Banco de dados

O banco SQLite é criado automaticamente na primeira execução em `route_planner/database/db.sqlite`.

## Configuração ORS

Defina `ORS_API_KEY` para geocodificação e preenchimento online do cache de distâncias.
