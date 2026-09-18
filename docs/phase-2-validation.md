# Validación de fase 2

Entorno: Windows, Python 3.14.5, uv 0.12.16, nflreadpy 0.1.5, Polars 1.44.2,
Streamlit 1.64.0 y pytest 9.1.1. Validación realizada el 18 de septiembre de 2026 UTC.

## Comprobaciones ejecutadas

- `uv sync --locked`: correcto; 54 paquetes en el entorno (incluidos transitivos).
- `uv run pytest`: 53 aprobadas, 2 integraciones excluidas; sin warnings de pytest.
- `uv run pytest -m integration`: 2 aprobadas, 53 excluidas.
- `uv run python -m compileall -q src scripts`: correcto.
- `git diff --check`: sin errores de espacios; Git avisa de conversión LF/CRLF en Windows.
- Revisión de imports: solo `data/nfl_data.py` importa nflreadpy; no hay imports de
  Pandas ni llamadas `to_pandas` en el código del proyecto.

Pruebas controladas: fechas sin partidos, semanas inválidas, temporadas, futuros
resultados excluidos, ventanas configurables, empates, sedes neutrales, estadísticas
incompletas, errores de conexión, H2H y alias de franquicia, joins de jugadores,
lesiones posteriores al corte, denominadores EPA, zona roja con nulos y navegación UI.

Los tests de integración recuperan calendario y estadísticas semanales de 2024.
No descargan PBP. La prueba real con PBP fue una ejecución manual explícita:

```bash
uv run python scripts/analyze_nfl.py --season 2024 --team BUF --opponent MIA --date 2024-11-03 --week 9 --pbp --matchup 2024_09_MIA_BUF --output .cache/phase2-real-validation.json
```

PBP 2024: **49.492 filas y 372 columnas**, DataFrame Polars. Se descargó una sola
temporada (aproximadamente 20,6 MB) mediante nuestra capa y nflreadpy. Las siguientes
consultas reutilizaron la caché. No se recalculó un modelo EPA ni se generaron predicciones.

## Ejemplo real de comprobación

Últimos cinco partidos de temporada regular anteriores al 3 de noviembre de 2024:

| Métrica | BUF | MIA |
| --- | ---: | ---: |
| Récord V–D–E | 3–2–0 | 1–4–0 |
| Puntos por partido | 23,6 | 13,4 |
| Puntos permitidos por partido | 19,6 | 21,8 |
| Yardas netas por partido | 341,0 | 295,0 |
| EPA por jugada | 0,137 | −0,181 |
| Success Rate | 44,0 % | 38,9 % |
| Jugadas ofensivas elegibles con EPA | 293 | 316 |

Ambos equipos tenían cinco resultados, cinco box scores y PBP de cinco partidos
en esta ventana. El resultado del propio enfrentamiento no entró en las métricas.
Registro numérico: [phase-2-real-check.json](phase-2-real-check.json).

La revisión real encontró `sack_yards_lost` negativo en origen. Se corrigió la
normalización antes de la validación final y se agregó un test de regresión. No se
introdujeron fixtures deportivos en la interfaz; los datos controlados solo viven en tests.

## Interfaz

Se inició `streamlit run scripts/run_dashboard.py` en localhost. Se verificó en el
navegador la cartelera actual, selección de temporada/semana, apertura de matchup,
resumen BUF–MIA 2024 y tabla EPA/Success Rate con cifras concordantes con Python.
Se comprobó un viewport de 390×844 y se restauró el tamaño de escritorio.
AppTest cubre además selección sin partidos, indisponibilidad de la fuente,
comparación directa, métricas avanzadas y regreso a la cartelera.

## Límites deliberados

Las definiciones y universos de las métricas están en [metrics.md](metrics.md).
Los informes de lesiones no constituyen un archivo histórico completo de lo
conocido antes del kickoff. Conferencias/divisiones proceden de un catálogo actual;
el flag divisional del calendario tiene prioridad para el partido. La zona roja es
una métrica definida por posesiones con snap elegible y no se presenta como un
recuento oficial idéntico al de todos los proveedores. No hay ajustes por fuerza
del rival ni resultados predictivos.
