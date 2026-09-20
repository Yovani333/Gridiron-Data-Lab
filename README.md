# Gridiron-Data-Lab

Actualización: [fiabilidad y evaluación heurística v0.2](docs/reliability-v02.md).
Evaluación adicional: [benchmarks sobre la misma muestra y rangos del score](docs/pick-benchmarks.md).
La sección Datos separa el backtest de Potential Picks del modelo logístico histórico.
Las probabilidades de ese modelo están suspendidas hasta reevaluarlo con las correcciones.
Python-based football analytics platform for collecting, validating and analyzing NFL game, team and historical data using nflreadpy.

## Estado actual

**Motor experimental y análisis descriptivo NFL.** Permite consultar partidos,
comparar equipos y evaluar un primer modelo probabilístico mediante backtesting
cronológico. La fuente sigue siendo exclusivamente nflverse/nflreadpy. El modelo
todavía no supera el benchmark de mejor récord y sus probabilidades no constituyen
picks ni recomendaciones. No hay API propia, base de datos externa ni cuotas.

## Abrir la interfaz temporal

```bash
uv sync
uv run streamlit run scripts/run_dashboard.py
```

Abrir la dirección local que indique Streamlit, normalmente `http://localhost:8501`.
GitHub muestra la documentación; no ejecuta esta aplicación Python automáticamente.
La interfaz corre localmente y no requiere un frontend JavaScript propio.

- **Inicio:** dashboard oscuro con próximos partidos, señales descriptivas,
  cobertura de datos, líderes y gráficas calculadas de calendarios y estadísticas.
- **Potential Picks / Posibles Picks:** resumen del mejor candidato en Inicio y
  detalle de Moneyline, Spread, Game Total y Team Total en cada matchup. El
  `Pick Score` es un índice explicable 0–100, **no un porcentaje de acierto**.
  Exige tres juegos previos por equipo; descarta señales débiles. Sin línea
  verificable muestra solamente Statistical Leans. Los totales se comparan con
  el promedio NFL anterior al corte, nunca con líneas inventadas. Pesos y mínimos
  en `analysis/pick_config.py`; factores favorables, contrapesos y faltantes visibles.
- **Jugadores y Estadísticas:** líderes Passing/Rushing/Receiving/Defense
  agregados por `player_id` en temporada regular; temporada seleccionable.
  Si no hay estadísticas publicadas, se indica; Inicio puede mostrar una
  temporada anterior y la identifica expresamente.
- **Partidos:** temporada, semana o fecha; tarjetas con equipos, marcador y estado.
- **Ver matchup:** forma reciente, ofensiva, defensiva, local/visitante, historial,
  lesiones y métricas avanzadas lado a lado.
- **Comparar equipos:** elegir dos equipos y una fecha de corte sin seleccionar partido.
- Ventanas de 1, 3, 5, N partidos o temporada completa; regular, playoffs o ambas.
- Historial de 3, 5, 10 o todos los enfrentamientos anteriores disponibles.
- **Incluir métricas avanzadas** habilita la carga de una temporada PBP completa.
  La primera carga puede tardar; los datos quedan cacheados.
- **Diagnóstico del modelo:** accuracy, Brier, log loss, calibración y benchmarks.
  La vista de matchup muestra una estimación experimental solo cuando existe
  muestra previa suficiente y el artefacto fue entrenado antes de la fecha.

Las comparaciones de un partido usan resultados **anteriores a su fecha**. No
incluyen ese resultado ni partidos posteriores. Los datos faltantes se muestran
como «No disponible», junto con la cobertura. El calendario ofrece resultados
publicados, no estado en vivo. Las fechas/horas se conservan como calendario NFL/ET.

Definiciones, denominadores y límites: [docs/metrics.md](docs/metrics.md).
Validación real: [docs/phase-2-real-check.json](docs/phase-2-real-check.json).
Metodología y límites del motor: [docs/model-v0_1.md](docs/model-v0_1.md).
Metodología de mercados y Pick Score: [docs/potential-picks.md](docs/potential-picks.md).

Exportar un reporte reproducible de Potential Picks:

```bash
uv run python scripts/analyze_picks.py --season 2024 --game-id 2024_14_BUF_LA --output .cache/picks-2024-14.json
```

La salida conserva fecha de corte, configuración, factores y resultado
retrospectivo frente a la referencia utilizada. No sobrescribe archivos previos.
No evalúa rentabilidad ni convierte el score en probabilidad.

## Evaluar el modelo

```bash
uv run python scripts/evaluate_model.py --seasons 2024 2025
uv run python scripts/evaluate_model.py --seasons 2024 2025 --ablation --output .cache/model-evaluation.json
uv run python scripts/analyze_model.py --season 2026 --team-a BUF --team-b MIA --as-of-date 2026-10-01 --home-team BUF
```

El segundo comando guarda resultados por partido y el análisis de eliminación
de variables; `.cache` es local e ignorado por Git. Para regenerar el artefacto
y el resumen visible en la interfaz, añadir `--model-output` seguido de
`src/nfl_analytics/config/model_v0_1.json` y `--diagnostics-output` seguido de
`src/nfl_analytics/config/model_v0_1_diagnostics.json`. Cada semana de evaluación
usa únicamente partidos anteriores a su primer juego y vuelve a ajustar el modelo. Las
fuentes retrospectivas pueden haber sido revisadas después de cada kickoff;
consulta los límites documentados antes de interpretar las cifras.

## Requisitos e instalación

Entorno comprobado en Windows: **Python 3.14.5**, **uv 0.12.16**,
**nflreadpy 0.1.5**, **Polars 1.44.2**, **pytest 9.1.1**.
La interfaz temporal utiliza **Streamlit 1.64.0**, declarado como dependencia directa.
Streamlit instala dependencias transitivas (entre ellas Pandas, Arrow y su servidor
interno); nuestro código de datos y análisis continúa usando Polars nativo y no
implementa endpoints ni convierte los DataFrames a Pandas.
`nflreadpy` requiere Python >=3.10; este proyecto usa Python 3.14 y fija la
serie 3.14 en `.python-version`. La versión 3.14.5 fue la probada localmente;
el despliegue puede usar otra versión de mantenimiento 3.14 disponible.
uv puede descargar un intérprete compatible si falta.

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
uv run pytest -m integration   # integración explícita: calendario y box scores 2024
uv run pytest -m ""            # toda la suite
```

El marker `integration` está registrado. La selección explícita reemplaza la
exclusión por defecto. Las unitarias bloquean conexiones de socket y usan fixtures
pequeñas; verifican argumentos, contratos, errores, delegación, operaciones Polars,
semana y convenciones de temporada en enero, playoffs y cambio de año de rosters.
La integración no descarga play-by-play y reutiliza la caché si está vigente.
Las pruebas de presentación usan AppTest con datos controlados y sin Internet;
se permite únicamente el socket loopback que necesita asyncio en Windows.
Resultado histórico de la fase descriptiva: **53 pruebas unitarias/presentación aprobadas y
2 integraciones aprobadas**. También se verificaron sincronización con lockfile,
sintaxis, consultas reales con PBP y la interfaz en escritorio y móvil.
Registro: [docs/phase-2-validation.md](docs/phase-2-validation.md).
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
nflverse -> nflreadpy -> nfl_analytics.data -> analysis -> presentation -> Streamlit

src/nfl_analytics/
    __init__.py
    data/__init__.py
    data/nfl_data.py          # único adaptador de nflreadpy
    data/games.py             # normalización y consultas de calendario
    data/stats.py             # contrato de estadísticas semanales
    data/players.py           # lesiones, identidades y joins
    data/teams.py             # alias de franquicias por ID del proveedor
    data/datasets.py          # disponibilidad y carga de temporada
    analysis/form.py         # ventanas, récord, head-to-head
    analysis/team_stats.py   # métricas ofensivas/defensivas
    analysis/play_by_play.py # EPA, éxito, explosivas, terceros downs, zona roja
    analysis/matchup.py      # composición descriptiva
    analysis/leaders.py      # líderes reales a partir de estadísticas semanales
    analysis/signals.py      # contraste descriptivo previo al partido
    analysis/signal_config.py # pesos y mínimos visibles, no calibrados
    analysis/matchup_evidence.py # evidencia pregame reutilizando perfiles existentes
    analysis/market_analysis.py # factores específicos por mercado y scoring
    analysis/market_lines.py  # contrato futuro de líneas verificadas, sin proveedor
    analysis/pick_engine.py   # filtros, candidatos y ranking
    analysis/pick_config.py   # metodología versionada y configurable
    analysis/pick_validation.py # liquidación de reportes congelados
    presentation/service.py # orquestación independiente de Streamlit
    presentation/dashboard.py
    presentation/matchup_view.py
    presentation/components.py
    presentation/picks_view.py # tarjetas y explicación de Potential Picks
scripts/explore_nfl_data.py
scripts/analyze_nfl.py
scripts/run_dashboard.py
tests/unit/test_nfl_data.py
tests/integration/test_nflreadpy_integration.py
docs/verified-data.json
```

La dependencia externa está aislada en `data/nfl_data.py`. No se crea `config/`
vacío: solo existe una configuración de caché, expuesta desde la misma frontera.
`analysis/` contiene funciones que reciben DataFrames y no realizan descargas.
La interfaz llama al servicio de presentación, que reúne datos y análisis; el
servicio puede reutilizarse o sustituirse al construir una interfaz definitiva.

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
nativas de Polars. Los loaders `load_*` conservan los contratos originales de fase 1;
las nuevas funciones `get_*` entregan datos normalizados para el análisis.

## Consultas y ejemplos de análisis

```python
from datetime import date, timedelta
from nfl_analytics.data import nfl_data
from nfl_analytics.data.datasets import season_data
from nfl_analytics.analysis import recent_form, compare_teams, head_to_head

nfl_data.configure_cache(".cache/nflreadpy")
today = date.today()
today_games = nfl_data.get_games_by_date(today)
yesterday_games = nfl_data.get_games_by_date(today - timedelta(days=1))
season = nfl_data.get_current_season()
schedule = nfl_data.get_games(season)
week_games = nfl_data.get_games_by_week(season, 2)
recent = nfl_data.get_recent_games("BUF", season, games=5, before=today)
form = recent_form(schedule, "BUF", games=3, before=today, venue="home")
data = season_data(season, include_pbp=False)
report = compare_teams(data, "BUF", "MIA", before=today, games=5, injury_week=2)
offense = report["team_a"]["offense"]
defense = report["team_a"]["defense"]
injuries = report["injuries"]["BUF"]
history = head_to_head(nfl_data.get_games(nfl_data.get_schedule_seasons()),
                       "BUF", "MIA", games=10, before=today, catalog=data.teams.frame)
```

Equipos/semanas de los ejemplos son parámetros ilustrativos, no constantes internas.
Para una comparación sin partido, las lesiones requieren seleccionar su semana.
`analyze_matchup(data, game_id)` determina los equipos, semana y fecha desde el partido.
Para relacionar estadísticas de jugadores: `attach_players(nfl_data.load_player_stats(season),
nfl_data.load_rosters(season))` desde `nfl_analytics.data.players`; usa IDs, equipo y temporada.

El script muestra consultas por fecha/semana, forma, historial, ofensiva, defensiva,
lesiones y comparación en una salida JSON:

```bash
uv run python scripts/analyze_nfl.py --team BUF --opponent MIA
uv run python scripts/analyze_nfl.py --season 2024 --team BUF --opponent MIA --date 2024-11-03 --week 9 --games 5 --pbp --matchup 2024_09_MIA_BUF --output .cache/comparison.json
```

La segunda orden es una demostración histórica reproducible con PBP optativo.
No hay descargas PBP en pytest ni al abrir la cartelera por defecto.

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

Se reutiliza la implementación de archivos de nflreadpy:

El dashboard agrega una caché de resultados en memoria de Streamlit de 15 minutos
(máximo cuatro conjuntos de análisis), sobre la caché de archivos de nflreadpy.
«Actualizar vista» limpia esa memoria, no fuerza una descarga remota. Para
forzar la actualización de un dataset puede usarse el explorador con `--refresh`.
La hora de lectura visible no es una garantía de la última actualización del origen.

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

Se podrá validar o descartar la regla descriptiva con evaluación cronológica,
estudiar fuerza del rival y ajustar las métricas por calendario. El motor
probabilístico experimental existente se mantiene separado y aún no supera
su benchmark de mejor récord. No se integran odds, parlays ni servicios externos.

### Identidad visual
Los logos y colores se obtienen de load_teams mediante nuestra capa nfl_data; las fotos provienen del campo headshot_url de estadísticas de jugadores. El navegador carga esas imágenes desde las URLs publicadas por nflverse (pueden alojarse en CDN de NFL/ESPN; no se consulta una API deportiva adicional). Los metadatos visuales se reutilizan durante 24 horas y su ausencia no bloquea el análisis. Se conservan abreviaturas/nombres cuando falta una imagen. Los colores del catálogo corresponden a la identidad actual, no a una reconstrucción histórica.

# Registro prospectivo

Para conservar señales antes de los partidos y evaluarlas posteriormente sin
recalcularlas, consulta [registro prospectivo](docs/prospective-tracking.md).
