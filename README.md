# Route Planner - Lavanderia Industrial

## Arquitetura refatorada (cache persistente por pares)

- `src/database/connection.py`: conexão SQLite
- `src/database/migrations.py`: criação automática do schema
- `src/services/openrouteservice_client.py`: cliente ORS com geocode + matrix batch
- `src/services/distance_matrix_service.py`: matriz dinâmica em memória com cache persistente em `distance_cache`
- `src/solver/ortools_solver.py`: solver OR-Tools compatível com callback de distância/tempo

## Inicializar banco (primeira execução)

```bash
python -c "from src.database.connection import get_connection; from src.database.migrations import initialize_database; c=get_connection(); initialize_database(c); print('ok')"
```

## Executar em desenvolvimento

```bash
python main.py
```

## Gerar executável Windows

```bash
pyinstaller --onefile --noconsole main.py
```

## Configuração ORS

Defina `ORS_API_KEY` para geocodificação e preenchimento online de pares ausentes no `distance_cache`.

Sem internet/API, o sistema continua funcionando para pares já cacheados.
