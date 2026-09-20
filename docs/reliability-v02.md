# Fiabilidad y evaluación v0.2

Esta fase conserva nflreadpy como única fuente. No entrena modelos ni obtiene odds.

## Correcciones

- Lesiones: corte exclusivo por fecha; se excluye todo el día del encuentro.
  Reportes sin `date_modified` se identifican como no verificables, no como ausencia de lesiones.
- Sedes neutrales: sin variable de localía en la generación de ejemplos ni en la llamada de la UI.
- El modelo exige cobertura de box scores propios y del rival igual a la ventana de resultados.
- H2H: REG/POST se filtra antes de limitar N encuentros. El motor de picks sigue limitado a REG.
- Inicio propaga ventana, tipo de temporada e historial; Estadísticas usa el calendario del año seleccionado.
- PBP duplicado por game_id/play_id se rechaza antes de agregar.
- La fecha de cada predicción retrospectiva es la del partido, no la del comienzo de la semana.
- Las salidas del evaluador no sobrescriben artefactos existentes.
- Partidos del día sin marcador se etiquetan como tales; no se afirma que ya comenzaron.

## Definiciones

`win_pct` conserva victorias/partidos para no cambiar silenciosamente las reglas.
`standings_pct` añade (victorias + 0.5 * empates)/partidos y se muestra separado.
Touchdowns significa TD ofensivos de pase/carrera. Turnovers significa intercepciones
lanzadas + fumbles perdidos; la defensa muestra esas pérdidas del rival, no solamente
recuperaciones realizadas por la unidad defensiva. Red zone sigue siendo TD por
posesión con snap de scrimmage dentro de la yarda 20; no se afirma equivalencia con
la estadística oficial. Los denominadores y la cobertura deben acompañar la comparación.

Puntos por drive utiliza `fixed_drive_result`: TD ofensivo = 6, field goal = 3,
otros resultados reconocidos = 0. Excluye conversiones, safeties y touchdowns del
rival. Cuenta posesiones con pase, carrera, kneel o spike; una posesión exclusivamente
de equipos especiales no entra. Resultados desconocidos/conflictivos invalidan la
métrica en lugar de transformarse en cero. No es el total del marcador dividido
entre drives. Se comprobó con PBP 2024 ya almacenado, sin nuevas descargas masivas.

Descanso usa home_rest/away_rest del calendario. El contraste de eficiencia muestra
ofensiva propia y producción permitida por el rival; su diferencia no es una
predicción. Solo se calcula con cobertura completa de partidos. Estos nuevos
indicadores no reciben pesos dentro del Pick Score.

## Evaluación heurística

```bash
uv run python scripts/evaluate_picks.py --seasons 2024 2025 --games 5 --output .cache/evaluation-new.json
```

Cada encuentro usa exclusivamente partidos anteriores a su fecha. Los resultados
del encuentro entran después, en la liquidación. El reporte guarda configuración,
versión, IDs de entrada, cortes, huellas SHA-256 de calendarios y estadísticas,
decisiones, abstenciones y resultados agrupados por mercado y bandas de score.
Las huellas permiten identificar una entrada, pero no archivan por sí solas sus
bytes. Hay que conservar los datasets originales para reproducción exacta a largo plazo.

Se ejecutaron 544 encuentros REG de 2024–2025. Los diagnósticos compactos están en
`config/picks_v0_2_diagnostics.json`; el reporte completo generado localmente está
en `.cache/picks-v02-evaluation.json`. En la UI se muestran en Datos, separados del
diagnóstico logístico. Team Total tiene dos oportunidades por partido.

Moneyline: 113/153 resultados favorables en 2024; 101/147 en 2025, excluyendo un empate.
No son porcentajes sobre todos los partidos: hubo 119 y 124 abstenciones respectivamente.
Spread sin línea evalúa exclusivamente preferencia de ganador; NO es ATS.
Totales se contrastan con el promedio de liga anterior; NO son aciertos contra una
línea de sportsbook. Ninguna cifra representa rentabilidad o probabilidad calibrada.
Estas temporadas ya eran conocidas durante desarrollo: esto es un diagnóstico
retrospectivo, no una validación prospectiva independiente ni evidencia de ventaja.

El modelo logístico v0.1 conserva sus archivos para auditoría, pero la UI suspende
sus probabilidades hasta reevaluarlo con las correcciones de localía y cobertura.
El acceso de investigación y los scripts anteriores permanecen disponibles.

## Límites pendientes

Los datos históricos pueden incluir revisiones: filtro por fecha no equivale a
archivo point-in-time. El caché de origen sigue siendo de 24 h; Actualizar vista
solo limpia Streamlit. La calibración de pesos, benchmarks en muestras iguales,
intervalos de incertidumbre, evaluación prospectiva y líneas verificadas siguen
siendo pasos futuros. No combinar scores como probabilidades de parlays.
