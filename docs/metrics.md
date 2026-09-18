# Contratos y metodología del análisis descriptivo

## Alcance y fuente

Fuente exclusiva: nflverse a través de nflreadpy 0.1.5. Los loaders y las llamadas
al proveedor viven en `data/nfl_data.py`. La capa `analysis` recibe Polars DataFrames;
no accede a Internet ni importa Streamlit. `presentation/service.py` coordina esas
capas; las vistas renderizan resultados y estados de disponibilidad.

No hay probabilidades de victoria, señales de apuestas ni un modelo entrenado por
este proyecto. EPA utiliza los valores publicados por nflverse, cuya metodología
upstream incorpora un modelo de puntos esperados; consumir esa columna no equivale
a crear aquí un predictor de resultados.

## Partidos, fechas y ventanas

- Una fila por `game_id`; fecha y equipos obligatorios. Los scores permanecen
  nulos hasta que el proveedor publique ambos.
- `result_available`: ambos marcadores presentes. `awaiting_update`: fecha pasada
  o actual sin ambos marcadores. `scheduled`: fecha futura sin resultado. Son
  estados derivados; no distinguen partido en vivo, aplazamiento o retraso del feed.
- Ganador/perdedor nulos en empate o sin resultado; margen absoluto de marcadores
  si hay resultado. No confundirlo con el diferencial desde la perspectiva de un equipo.
- La fecha es `gameday` del calendario NFL; `gametime` es la hora del calendario
  en ET. No se convierte automáticamente a la zona horaria del visitante.
- `before` es exclusivo: se excluye todo partido de esa fecha o posterior. Para
  matchup se usa su propia fecha. Los datos subyacentes siguen siendo retrospectivos,
  con posibles correcciones del proveedor: no existe un archivo point-in-time para backtesting.
- Ventanas 1, 3, 5, N o todos los partidos disponibles de la temporada y tipo elegidos.
  No se completan cinco partidos con años anteriores al empezar una temporada.
- POST comprende WC, DIV, CON, SB (y POST si aparece). Los splits local/visitante
  excluyen sedes neutrales aunque el calendario asigne un local administrativo.

## Récord y forma

| Métrica | Definición |
| --- | --- |
| Partidos jugados | Resultados con ambos marcadores dentro del filtro |
| Victorias / derrotas / empates | Comparación de puntos del equipo y rival |
| Porcentaje de victorias | Victorias / partidos; empate cuenta como partido, no como media victoria |
| Puntos a favor / en contra | Suma de los marcadores correspondientes |
| Promedios | Suma / partidos con resultado |
| Diferencial | Puntos a favor − en contra; promedio dividido entre partidos |

Sin partidos se devuelve conteo cero y métricas de puntos/porcentajes `None`, no un
rendimiento ficticio de cero puntos por partido. Historial y forma conservan los juegos.

## Estadísticas de equipos

Se cruzan las estadísticas semanales por `(game_id, team)`. Para defensa se cruzan
las filas del **oponente de cada juego**. Se valida unicidad por partido/equipo.
Los promedios de estadísticas usan partidos con box score, que pueden ser menos
que los partidos del calendario. La cobertura se muestra separada por lado.

| Métrica | Cálculo |
| --- | --- |
| Yardas netas totales | Passing yards + rushing yards − magnitud de sack yards lost |
| Yardas netas por partido | Yardas netas / partidos con estadísticas |
| Jugadas de box score | Attempts + carries + sacks suffered |
| Yardas por jugada | Yardas netas / suma de jugadas, nunca promedio simple de promedios |
| Pase/carrera por partido | Yardas respectivas / partidos con estadísticas |
| Touchdowns ofensivos | Passing TD + rushing TD; no se vuelve a sumar receiving TD |
| Pérdidas de balón | Passing interceptions + fumbles lost total |
| Pérdidas del rival | Esa misma métrica del oponente; incluye pérdidas en equipos especiales |
| Completions / attempts | Sumas del proveedor |
| Sacks permitidos / al rival | Sacks suffered propios / del oponente |

**Convención verificada:** `sack_yards_lost` es negativa en el dataset probado.
`get_team_stats` la normaliza a magnitud positiva; `load_team_stats` sigue entregando
el valor original. Los análisis de box score esperan el contrato normalizado.
No se suma `receiving_yards` a passing yards ni se duplican fumbles por tipo.

Si una columna falta o tiene valores nulos en la muestra agregada, su total y las
métricas dependientes son `None`. El código no convierte un total desconocido en cero.
Los primeros downs completos (incluidos los de penalización), third down y zona
roja se calculan con PBP; no se estiman sumando únicamente passing/rushing first downs.

## Play-by-play

Se descarga una sola temporada mediante `load_play_by_play(season)`. La UI requiere
activar sus métricas; nflreadpy no permite descarga por semana. Después se filtran
solo `game_id` de la misma muestra usada para el análisis.

**Jugadas elegibles para EPA y explosivas:** `play_type` pass/run, sin kneel,
spike ni intento de dos puntos. No se incluyen kicks, punts ni `no_play`.
Los sacks y scrambles cuentan como dropbacks cuando `qb_dropback=1`.
Carrera diseñada: jugada elegible con `qb_dropback=0`.

| Métrica | Denominador / definición |
| --- | --- |
| EPA/play | Media de EPA finito y no nulo en jugadas elegibles |
| EPA de pase/carrera | Media y total según dropback/carrera diseñada |
| Success Rate | Jugadas con EPA > 0 / jugadas con EPA válido; EPA cero no es éxito |
| Explosive play rate | Dropback ≥20 yardas o carrera diseñada ≥10, dividido entre jugadas con yardas y clasificación conocidas |
| EPA / éxito defensivo | Valores ofensivos del rival permitidos; no se invierte el signo |
| Third-down efficiency | Converted / (converted + failed), usando flags del proveedor para incluir conversiones por penalización |
| First downs | Suma del flag `first_down` informado, incluidos primeros downs por penalización |
| Zona roja | Posesiones con al menos una jugada elegible iniciada a ≤20 yardas; TD ofensivo en esa posesión / esas posesiones |

Zona roja agrupa por partido, `fixed_drive` y equipo con posesión. No cuenta una
pick-six como TD ofensivo ni varias jugadas como varias visitas. Es una definición
operativa reproducible de visitas con snap, **no una promesa de equivalencia con
la estadística oficial**: puede excluir entradas que solo tengan penalización,
rodilla o field goal. Si faltan campos necesarios, se muestra no disponible.

Se reportan juegos con PBP, jugadas elegibles y jugadas con EPA. El total EPA exige
que todos los EPA de su muestra sean conocidos; la media puede usar el subconjunto
válido. No se usa media de promedios de juegos. Las estadísticas de box score y
PBP tienen universos distintos y pueden no coincidir (kneels, penalizaciones, etc.).

## Historial, conferencia y división

H2H usa el calendario completo publicado (archivo pequeño) y una fecha de corte;
permite 3, 5, 10 o todos. Con catálogo, relaciona abreviaturas históricas que
comparten `team_id`, conservando los nombres originales en las filas del historial.
No hay mapa de equipos hardcodeado. Sin catálogo solo se comparan abreviaturas exactas.

Conferencia y división proceden de `load_teams`, que describe una alineación actual,
no una tabla histórica por año. Para un matchup se prioriza el flag `div_game` del
partido. Si contradice una inferencia divisional del catálogo, se indica que falta
alineación histórica. Una etiqueta de conferencia no expresa fuerza ni ventaja.

## Jugadores y lesiones

Se normalizan jugador, ID, equipo, posición, semana, lesión, estado del informe,
estado de práctica y fecha del reporte. La participación de práctica no es prueba
de participación real en el partido; no se asignan pesos de impacto.

Los joins usan `(season, team, player_id)`, nunca nombres. Los IDs nulos se conservan
en datos originales, pero no se emparejan con roster. El directorio deduplica esas
claves y preserva filas al hacer left join; no pretende reconstruir transferencias
o posiciones exactas a una hora histórica.

Lesiones se filtran por equipo, semana y `reported_at` hasta el día elegido. Un
informe sin fecha o posterior al corte no se presenta como conocido entonces.
Los archivos retrospectivos pueden haber sido reemplazados después: una selección
vacía significa **sin informes verificables**, no «ningún lesionado».

## Disponibilidad, pruebas y evolución

Un error del calendario muestra indisponibilidad general. Fallos de estadísticas,
PBP, rosters o lesiones se conservan como estados separados y no ocultan el calendario.
Las funciones puras se verifican con fixtures pequeñas y cálculos manuales,
incluyendo empates, neutralidad, futuras fechas, datos nulos y tasas sin denominador.
La interfaz se prueba con Streamlit AppTest y se verifica visualmente en navegador.

Se retienen oponente, temporada y `game_id` para futuros ajustes por fuerza del rival.
No se implementaron rankings, strength of schedule ni ajustes de oponente todavía.

Fuentes oficiales contrastadas con el paquete instalado:

- [nflreadpy: loaders](https://nflreadpy.nflverse.com/api/load_functions/).
- [nflfastR: estadísticas y cambios de nombres](https://nflfastr.com/articles/stats_variables.html).
- [nflfastR: definición de campos PBP](https://nflfastr.com/articles/field_descriptions.html).
- [Streamlit: AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).
