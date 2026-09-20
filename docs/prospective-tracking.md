# Registro prospectivo

Los backtests existentes son retrospectivos. Este registro congela las señales
observadas antes del partido, sin cambiar pesos ni entrenar modelos.

```powershell
uv run python scripts/track_picks.py record --season 2026 --days 7
uv run python scripts/track_picks.py settle --season 2026 --output records/evaluation-2026-09-28.json
```

La temporada y el horizonte son configurables. `record` selecciona **todos** los
partidos REG entre mañana y los próximos N días, incluidos los que producen
abstenciones. No registra juegos de hoy: el calendario normalizado no ofrece un
timestamp de kickoff verificado y se adopta un corte conservador por fecha UTC.
El reloj real de captura no se puede sustituir mediante argumentos del comando.

Cada archivo contiene fecha de captura, versión, configuración, factores,
referencias estadísticas, IDs de partidos utilizados, benchmarks calculados antes
del partido y los DataFrames de entrada serializados. Solo entran al análisis
resultados de fechas anteriores al día de captura. Se usan schedules, estadísticas
de equipos y metadatos de nflreadpy; no se descarga PBP ni lesiones en este flujo.
Se fuerza refresco de caché al ejecutar el comando; no hay nuevos proveedores.

Se conserva una observación por partido/versión. Repetir el comando preserva el
primer archivo. El SHA-256 permite detectar alteraciones accidentales; **no es
una firma ni un sello temporal externo**. Respaldar `records/` y, si se requiere
auditoría independiente, publicar los hashes antes de los partidos.

`settle` nunca recalcula señales: usa los valores congelados y resultados nuevos.
Genera otro archivo (no sobrescribe), mantiene pendientes y revisa cambios de fecha
que invalidarían la captura. Descarta duplicados y versiones mezcladas. Los
benchmarks y bandas utilizan las mismas reglas de la evaluación histórica.
Los resultados publicados pueden revisarse posteriormente: conservar cada informe.

No interpretar el score como probabilidad. Spread sin línea es una señal de lado;
totales se contrastan con la referencia de liga congelada, no con líneas de mercado.
No hay ATS, ROI ni evidencia nueva hasta que los partidos registrados terminen.

Los archivos quedan en `records/`, fuera de Git para evitar subir datasets grandes.
No se guardan en caché ni dependen del disco efímero de Streamlit. Ejecutar estos
comandos desde una computadora con almacenamiento persistente y respaldos.
Esta implementación no instala una tarea programada: ejecutar `record` antes de
cada jornada y `settle` después de publicarse los resultados.
