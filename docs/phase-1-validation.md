# Cierre de verificaciones de fase 1

## Instalación desde un clon limpio

Se clonó desde `https://github.com/Yovani333/Gridiron-Data-Lab.git` el commit
`5e24617060811f2f54bd011c59f7153f6a3b9860` en `.cache/clean-clone-validation`.
Antes de instalar se comprobó que no existían `.venv` ni `.cache` dentro del clon.
Se configuró `UV_CACHE_DIR` a `.cache/uv-fresh` dentro del clon para no reutilizar
la caché de paquetes anterior. Se reutilizaron únicamente el ejecutable uv y el
intérprete Python 3.14.5 instalado en la computadora.

Resultados:

| Comprobación | Resultado |
| --- | --- |
| `uv sync --locked` | 24 paquetes instalados desde una caché nueva |
| `uv sync` | Correcto, lockfile sin cambios |
| Imports `nflreadpy` y `nfl_analytics` | Rutas dentro del clon y su `.venv` |
| `uv run pytest` | 31 aprobadas, 1 integración excluida |
| `uv run python scripts/explore_nfl_data.py` | Calendario 2024: 285 filas, 46 columnas |
| `uv run pytest -m integration` | 1 aprobada, 31 unitarias excluidas |
| `git status --porcelain` dentro del clon | Sin cambios |

La primera exploración descargó el calendario porque tampoco existía caché de
datos. La integración posterior reutilizó ese archivo. Se validó una instalación
limpia en la misma computadora Windows, no una matriz de otros sistemas operativos.
El clon auxiliar y sus entornos permanecen ignorados por Git.

## Esquema real de play-by-play

Archivo inspeccionado:
`https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2024.parquet`.
Tamaño publicado: 20.597.560 bytes.

Se leyeron los últimos 8 bytes con un rango absoluto y después el footer Parquet
con otro rango absoluto. Ambas respuestas fueron HTTP 206. El diagnóstico rechazaba
respuestas que ignorasen el rango, por lo que no hubo descarga completa accidental.
Polars interpretó el esquema del footer: **372 columnas**. Tráfico de cuerpos HTTP:
**117.854 bytes** en total, aproximadamente 0,57 % del archivo completo.

El primer intento con rango relativo había recibido HTTP 501; usar posiciones
explícitas resolvió ese problema. No se cambió el proveedor ni la capa productiva.

| Columna comprobada | Tipo Polars |
| --- | --- |
| `game_id` | String |
| `play_id` | Float64 |
| `season` | Int32 |
| `week` | Int32 |
| `posteam`, `defteam` | String |
| `epa`, `success`, `cpoe` | Float64 |

El esquema completo se conserva en [pbp-2024-schema.json](pbp-2024-schema.json).
No se descargaron filas PBP ni se calcularon métricas. La disponibilidad de columnas
no demuestra que todas sus filas estén informadas ni sustituye la futura validación
de contenido. El wrapper de carga completa mantiene pruebas unitarias; no se añadió
una integración que descargue PBP en cada ejecución.
