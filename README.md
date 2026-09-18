# Gridiron-Data-Lab
Python-based football analytics platform for collecting, validating and analyzing NFL game, team and historical data using nflreadpy.

## Estado actual

**Fase 1 — Data foundation con nflreadpy.** Paquete Python para obtener, explorar y
validar datos NFL con Polars. El código reutilizable está separado de la exploración.
Todavía no se implementan análisis avanzados, backend, interfaz web ni modelos.

## Requisitos e instalación

Entorno comprobado en Windows: **Python 3.14.5**, **uv 0.12.16**,
**nflreadpy 0.1.5**, **Polars 1.44.2**, **pytest 9.1.1**.
`nflreadpy` requiere Python >=3.10; este proyecto usa Python 3.14 y fija 3.14.5
en `.python-version`, la versión disponible y probada. No se afirma compatibilidad
probada con otras versiones. uv puede descargar ese intérprete si falta.

Instalar [uv siguiendo sus instrucciones oficiales](https://docs.astral.sh/uv/getting-started/installation/)
y ejecutar:

```bash
git clone https://github.com/Yovani333/Gridiron-Data-Lab.git
cd Gridiron-Data-Lab
uv sync
uv run pytest
uv run python scripts/explore_nfl_data.py
```

`uv sync` crea `.venv`, instala el paquete en modo editable y las dependencias de
desarrollo. `uv.lock` se versiona; para exigir que no cambie, usar `uv sync --locked`.
Python no necesita paquetes globales. `nflreadpy` y `polars` son dependencias
directas; pytest está en el grupo `dev`; Hatchling es solo el backend de construcción.
La primera instalación y las descargas sin caché requieren Internet.

En el entorno original de Codex uv no estaba en PATH: se instaló únicamente uv
en `.cache/uv-bootstrap`, mediante un venv auxiliar, y todas las dependencias del
proyecto se instalaron con uv en `.venv`. Ese bootstrap es local, ignorado por Git
y no es necesario al clonar en otra computadora con uv instalado.
Para usarlo en la sesión PowerShell original:

```powershell
$env:Path = "$PWD\.cache\uv-bootstrap\Scripts;$env:Path"
uv sync
```

## Pruebas

```bash
uv run pytest                  # unitarias, sin red
uv run pytest -m integration   # integración explícita: calendario 2024
uv run pytest -m ""            # toda la suite
```

El marker `integration` está registrado. La selección explícita reemplaza la
exclusión por defecto. Las unitarias bloquean conexiones de socket y usan fixtures
pequeñas; verifican argumentos, contratos, errores, delegación, operaciones Polars,
semana y convenciones de temporada en enero, playoffs y cambio de año de rosters.
La integración no descarga play-by-play y reutiliza la caché si está vigente.
Resultado de la validación inicial: **31 unitarias aprobadas y 1 integración
aprobada**; sincronización normal y `--locked`, imports y exploración exitosos.
También se repitió todo desde un clon nuevo de GitHub, con `.venv` nueva y caché
de uv independiente. Véase [el registro de cierre](docs/phase-1-validation.md).

## Explorar datos

```bash
uv run python scripts/explore_nfl_data.py
uv run python scripts/explore_nfl_data.py --context
uv run python scripts/explore_nfl_data.py --dataset rosters --season 2024
uv run python scripts/explore_nfl_data.py --dataset player_stats --season 2024 --full-schema
uv run python scripts/explore_nfl_data.py --dataset team_stats --season 2024
uv run python scripts/explore_nfl_data.py --dataset injuries --season 2024
uv run python scripts/explore_nfl_data.py --dataset teams
```

Por defecto solo obtiene calendario 2024, una temporada histórica estable. Muestra
dimensiones, 20 columnas de esquema, cinco filas y valores/nulos relevantes.
`--full-schema` lista todo el esquema; `--context` añade temporada/semana actual e
inventario del calendario; `--refresh` fuerza actualización de los datasets solicitados.
Las tablas usan bordes ASCII para compatibilidad con consolas Windows.

La prueba manual de play-by-play es optativa y descarga una temporada completa:

```bash
uv run python scripts/explore_nfl_data.py --dataset play_by_play --season 2024 --allow-pbp
```

## Arquitectura e interfaz

```text
nflverse -> nflreadpy -> nfl_analytics.data -> analysis (futuro)

src/nfl_analytics/
    __init__.py
    data/__init__.py
    data/nfl_data.py
    analysis/__init__.py
scripts/explore_nfl_data.py
tests/unit/test_nfl_data.py
tests/integration/test_nflreadpy_integration.py
docs/verified-data.json
```

La dependencia externa está aislada en `data/nfl_data.py`. No se crea `config/`
vacío: solo existe una configuración de caché, expuesta desde la misma frontera.
`analysis/__init__.py` reserva deliberadamente el espacio de análisis futuro.

```python
import polars as pl
from nfl_analytics.data import configure_cache, load_schedules

configure_cache(".cache/nflreadpy")  # opcional para consumidores; persistente
games = load_schedules(2024)
chiefs_home = games.filter(pl.col("home_team") == "KC")
print(chiefs_home.select("game_id", "week", "home_score", "away_score"))
```

También funciona `from nfl_analytics.data.nfl_data import load_schedules`.
La interfaz pública incluye:

- `load_schedules(seasons)`, `load_rosters(seasons)`, `load_injuries(seasons)`.
- `load_player_stats(seasons, *, summary_level="week")` y `load_team_stats(...)`.
- `load_play_by_play(season)`: exclusivamente un entero, una temporada por llamada.
- `load_teams()`: nombres, abreviaturas, conferencia y división.
- `get_current_season(roster=False)`, `get_current_week()`.
- `get_schedule_seasons()`, `get_latest_completed_week(season)`.
- `configure_cache(directory, duration=86400)` y `NFLDataError`.

Los loaders con `seasons` aceptan entero o lista no vacía de enteros. Rechazan
booleanos, `None`, años fuera del intervalo admitido y eliminan duplicados.
No ofrecen el `True` upstream que dispara descargas de todos los años.
Las estadísticas admiten `week`, `reg`, `post`, `reg+post`.
Un año aceptado no garantiza que exista su archivo remoto.

La capa verifica DataFrame, columnas esenciales y resultado no vacío. Los errores
de entrada son `ValueError`; fallos del proveedor/esquema/dataset vacío generan
`NFLDataError` conservando la causa original. No sustituye fallos por datos inventados
ni convierte resultados a Pandas. No elimina identificadores nulos automáticamente.
Los consumidores usan `filter`, `select`, `group_by`, `join`, `sort` y demás operaciones
nativas de Polars; no hay cálculos estadísticos propios en esta fase.

## API real de nflreadpy investigada

Se inspeccionaron firmas y código de la instalación **0.1.5**, incluidos
`load_stats.py`, `utils_date.py`, `config.py`, `cache.py` y `downloader.py`.
Las firmas completas públicas y los esquemas realmente obtenidos están en
[docs/verified-data.json](docs/verified-data.json).

| Función real del proveedor | Parámetros/defaults | Disponibilidad observada |
| --- | --- | --- |
| `load_schedules` | `seasons=True` | calendario 1999–2026 |
| `load_player_stats` | `seasons=None, summary_level="week"` | archivos desde 1999, incluidos 2026 semanales |
| `load_team_stats` | `seasons=None, summary_level="week"` | archivos desde 1999, incluidos 2026 semanales |
| `load_rosters` | `seasons=None` | archivos 1920–2026 |
| `load_injuries` | `seasons=None` | archivos 2009–2026 |
| `load_pbp` | `seasons=None` | archivos 1999–2026 |
| `load_teams` | sin parámetros | metadatos, sin temporada |
| `get_current_season` | `roster=False` | convención de fecha NFL |
| `get_current_week` | `use_date=False, **kwargs` | semana según resultados pendientes |

Los loaders indicados retornan `polars.DataFrame`. Upstream acepta
`int | list[int] | bool | None` para temporadas. `load_schedules` obtiene
`schedules/games.parquet` completo y filtra después; los demás loaders estacionales
obtienen un Parquet por temporada y resumen. `load_pbp` no permite particionar por
semana ni seleccionar columnas antes de descargar.

El inventario se consultó en los releases de GitHub el **18 de septiembre de 2026 UTC**;
es evidencia de archivos publicados, no de cobertura completa o calidad de cada año.
No existe un inventario público general de temporadas en esta versión de nflreadpy.
`get_schedule_seasons()` deriva las presentes en el calendario; `max(...)` identifica
su última temporada. Para otros datasets debe verificarse el release correspondiente;
la temporada actual no garantiza disponibilidad. No se descargaron todas las temporadas.

Play-by-play 2024 figuraba con **20.597.560 bytes**. Se inspeccionaron función,
parámetros e inventario y se verificó su esquema real mediante dos solicitudes
HTTP Range con posiciones de bytes explícitas. Se transfirieron **117.854 bytes**
del footer, sin descargar filas de juego ni la temporada completa. Los rangos
relativos habían producido HTTP 501; los rangos explícitos funcionaron.
El esquema contiene **372 columnas**, incluidas `game_id`, `play_id`, `season`,
`week`, `epa`, `success` y `cpoe`, y está registrado en
[docs/pbp-2024-schema.json](docs/pbp-2024-schema.json).
Esto verifica nombres y tipos, no los valores ni la calidad de las filas;
la prueba del wrapper PBP sigue siendo unitaria, no integración con carga completa.

Fuentes oficiales para ampliar o actualizar la investigación:

- [API de nflreadpy](https://nflreadpy.nflverse.com/api/load_functions/).
- [Código del paquete](https://github.com/nflverse/nflreadpy).
- [Inventario de datasets](https://github.com/nflverse/nflverse-data/releases).
- [Diccionario play-by-play](https://nflreadr.nflverse.com/articles/dictionary_pbp.html).
- [Descripción de columnas nflfastR](https://nflfastr.com/articles/field_descriptions.html).

## Temporada y semana

`get_current_season()` delega en la convención real de nflreadpy: el año cambia el
jueves posterior a Labor Day. Enero y el Super Bowl pertenecen al año anterior;
la convención mantiene ese año durante el offseason. `roster=True` cambia el 15
de marzo. Es una convención basada en la fecha local, no una consulta de partidos.

Nuestra semana actual se deriva del calendario: primera semana con un marcador
pendiente; si todos tienen resultado, última semana programada. Replica el criterio
de la función del proveedor usando ambos marcadores. No es un reloj de partidos
en vivo y puede verse afectada por aplazamientos o demoras en resultados. Evitamos
`use_date=True`, cuya implementación aproxima semanas desde el primer jueves de
septiembre y no es equivalente a la fecha usada para cambiar de temporada.

`get_latest_completed_week(season)` devuelve la última semana con **al menos un**
partido con ambos marcadores, o `None` si no hay resultados; no implica que toda la
semana haya terminado. La última semana programada puede obtenerse con
`load_schedules(season).get_column("week").max()`.
En la verificación: temporada actual 2026, semana pendiente 2; para 2024, última
semana con resultados 22. Estos valores son observaciones, no constantes del código.

## Datos reales comprobados

Todos mediante nuestra capa; tipo `polars.DataFrame`:

| Dataset | Temporada | Filas | Columnas |
| --- | --- | ---: | ---: |
| Calendario/resultados | 2024 | 285 | 46 |
| Rosters | 2024 | 3.216 | 36 |
| Estadísticas de jugadores, semana | 2024 | 18.983 | 150 |
| Estadísticas de equipos, semana | 2024 | 570 | 138 |
| Lesiones | 2024 | 6.215 | 16 |
| Metadatos de equipos | sin temporada | 36 | 16 |

Los seis Parquet remotos sumaban aproximadamente 2,22 MB. Hay 22 `player_id`
nulos en las estadísticas y un `gsis_id` nulo en rosters; no deben eliminarse ni
interpretarse como ceros por defecto. Los metadatos incluyen abreviaturas históricas,
por eso no se valida que haya exactamente 32 filas.

## Caché y eficiencia

Se reutiliza la implementación de nflreadpy, sin caché propia:

- Upstream usa **memoria** por defecto: solo reutiliza durante ese proceso.
- Exploración e integración llaman a `configure_cache` y usan
  **`.cache/nflreadpy/` en la raíz del repositorio**, ignorada por Git. Otros
  consumidores deben llamar a esa función si desean el mismo comportamiento.
- En modo filesystem guarda DataFrames como Parquet con nombres hash de URL y
  parámetros. No conserva aparte una copia del archivo HTTP original ni utiliza
  una base de datos. Los bytes descargados se procesan en memoria.
- La vigencia predeterminada es **86.400 segundos (24 horas)**, basada en la fecha
  de escritura del archivo. Dentro de ese plazo lee el Parquet local sin red;
  al vencer elimina esa entrada y vuelve a descargar en la siguiente consulta.
  No comprueba ETag ni modificaciones remotas durante la vigencia.
- `duration=0` fuerza descarga en cada lectura; `--refresh` aplica esa opción solo
  a la ejecución actual. Puede conservar información desactualizada hasta vencer.
- nflreadpy también acepta `NFLREADPY_CACHE`, `NFLREADPY_CACHE_DIR`,
  `NFLREADPY_CACHE_DURATION`, `NFLREADPY_TIMEOUT` y `NFLREADPY_VERBOSE`, leídas
  al importar (también desde `.env`). Sin ruta propia usa el directorio de caché
  del sistema obtenido con platformdirs. El script reemplaza explícitamente modo,
  ruta y duración con sus valores documentados.
- La caché no es un archivo histórico garantizado. Un error de escritura puede
  ser silenciado por upstream si `verbose=False`; la siguiente llamada descargará
  otra vez. Se verificó la persistencia real leyendo los seis datasets en otro
  proceso **con conexiones de socket bloqueadas**.
- `nflreadpy.clear_cache()` existe. Sus ejemplos de filtros como `"pbp_2023"`
  no coinciden con las claves MD5 que genera 0.1.5; no se expone ese filtrado engañoso.

Evitar cargas de todos los años, reutilizar una temporada y seleccionar/filtrar en
Polars después. Filtrar semanas de PBP reduce el procesamiento posterior, no los
bytes descargados. No compartir archivos de caché ni `.venv` en Git.

## Próximas fases

Análisis estadístico, métricas avanzadas, backend e interfaz web se incorporarán
posteriormente como consumidores de esta capa. No forman parte de esta entrega.
