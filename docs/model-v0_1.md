# Motor experimental `model_v0_1`

La fuente es `nflreadpy`, encapsulada por `nfl_analytics.data`. El motor solo usa
temporada regular. Pretemporada y playoffs quedan excluidos del ajuste y del
backtest; no se extrapola su calibración.

## Features y corte temporal

`team_features` toma hasta cinco partidos REG completos por equipo, con fecha
**estrictamente anterior** a `as_of_date`. Requiere al menos tres partidos y tres
box scores por equipo. No rellena valores faltantes. Las diferencias son siempre
equipo A menos equipo B. En esta versión el modelo ajusta: porcentaje de victorias,
margen promedio, yardas por jugada, margen de turnovers, fuerza previa del rival y
localía. La fuerza del rival es el promedio del margen previo de cada rival **antes
del encuentro histórico respectivo**; omite encuentros sin historia anterior.
No hay pesos elegidos para estas variables: sus coeficientes proceden del ajuste.

La normalización usa media y desviación estándar de **solo los ejemplos de
entrenamiento**. La regresión logística se ajusta con descenso por gradiente
determinista y penalización L2 configurable. Cada juego aparece en el ajuste
desde ambas perspectivas; esto permite aprender el efecto de localía y hace
complementarias las probabilidades A/B. El Power Rating mostrado es la
contribución de las métricas propias del equipo al logit respecto a la media de
entrenamiento, sin localía; no es una escala 0–100 ni una predicción por sí sola.

EPA, Success Rate, splits de local/visitante, historial, división, conferencia y
lesiones están disponibles como contexto descriptivo. No entran en el ajuste
v0.1: PBP no siempre tiene cobertura uniforme y los reportes de lesiones
actualizados no constituyen una reconstrucción fiable del estado previo al
kickoff. No se infieren titulares ni impacto de lesiones. La arquitectura deja
esas variables listas para experimentos posteriores con cobertura verificable.

## Validación y límites

`walk_forward` agrupa por temporada y semana; entrena solo con ejemplos fechados
antes del primer juego de la semana evaluada. Los resultados de esa semana no
pueden alimentar sus otros juegos.
Los juegos empatados se excluyen de la etiqueta binaria. Los primeros encuentros
sin muestra suficiente se abstienen. Los benchmarks local, mejor récord y mejor
margen se evalúan en exactamente los mismos partidos. Las ablations vuelven a
entrenar y comparar al retirar cada variable; no se interpretan como causalidad.

El registro de evaluación está en
`src/nfl_analytics/config/model_v0_1_diagnostics.json` y el modelo entrenado
con todos los juegos elegibles de 2024–2025 en `model_v0_1.json`. El artefacto
solo puede utilizarse para fechas **posteriores** a su último partido de ajuste.
Para juegos históricos anteriores se requiere un artefacto ajustado solo con
temporadas anteriores; la interfaz se abstiene en vez de usar información futura.
El modelo mostrado en vivo fue ajustado con los datos publicados, y la evaluación
walk-forward es la medición fuera de muestra.

**Límite importante:** los archivos históricos de nflverse son retrospectivos y
pueden corregirse después de un partido. El filtro por fecha excluye partidos
futuros, pero no prueba qué versión exacta de un box score estaba publicada antes
de cada kickoff. Las fechas del calendario tampoco especifican el instante de
publicación. Por ello la evaluación es una simulación cronológica retrospectiva,
no una auditoría point-in-time del proveedor. No usar las probabilidades como
picks; se exige mejorar benchmarks, ampliar temporadas y verificar datos de
publicación antes de elevar el modelo a producción.

## Resultado verificado de esta versión

Con 2024 y 2025 hubo 447 juegos elegibles para entrenar el artefacto final y
403 predicciones walk-forward fuera de la semana usada para el ajuste. Accuracy:
65.5%; Brier: 0.2204; log loss: 0.6336. En los mismos 403 juegos, elegir al
equipo con mejor récord obtuvo 69.0% de accuracy, mejor margen 65.8% y siempre
local 54.1%. No se alcanza el criterio para emitir picks.

Al retirar la fuerza del rival, el Brier pasó a 0.2189; al retirar el margen de
turnovers, a 0.2195. Son resultados exploratorios sobre el mismo conjunto de
evaluación: seleccionar una variante por estas cifras y llamarla validada
introduciría sesgo. Se necesitan otras temporadas o una cohorte posterior para
confirmar cualquier cambio de variables. Los intervalos de calibración y todas
las ablations están en el JSON de diagnósticos.
