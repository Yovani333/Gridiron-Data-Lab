# Potential Picks — statistical_leans_v0_1

Esta versión añade reglas deterministas, no entrenamiento ni una probabilidad de
ganar/cubrir. Consume la comparación descriptiva existente. La interfaz muestra
un resumen en Inicio y los cuatro mercados en el detalle del matchup (Team Total
se evalúa separadamente para ambos equipos). El modelo probabilístico anterior
permanece independiente y no participa en esta puntuación.

## Fuentes comprobadas

`nflreadpy 0.1.5` se consume exclusivamente mediante `data/nfl_data.py`.

| Fuente existente | Uso |
| --- | --- |
| Calendario: game_id, season, week, game_type, gameday, home/away_team, home/away_score, location, div_game | Resultados, puntos, márgenes, fecha de corte, local/visitante y contexto divisional |
| Estadísticas semanales normalizadas: game_id, team, passing_yards, rushing_yards, sack_yards_lost, attempts, carries, sacks_suffered | Yardas netas por jugada ofensivas menos permitidas, solo si cubren toda la ventana de ambos equipos |
| Catálogo: team_conf, team_division y alias de franquicia | Conferencia, división y relaciones del H2H; sin bonus por pertenecer a una conferencia |
| Lesiones normalizadas: reported_at, team, position | Informes anteriores al día de corte; contexto sin peso inventado de impacto |

Se inspeccionó una carga real del calendario 2024: 285 filas, con
`home_moneyline`, `away_moneyline`, `spread_line`, `home_spread_odds`,
`away_spread_odds`, `total_line`. **Que estas columnas existan no acredita cuándo
estuvo disponible una cotización.** No hay un timestamp de observación de cada
línea, ni un campo team total en ese archivo. La normalización actual las excluye
del flujo descriptivo. No se reutilizan retrospectivamente como si hubieran sido
conocidas en cualquier fecha previa al kickoff.

No se descargan cuotas de otra fuente, no se calculan props y no se solicita PBP
para esta sección. La ausencia de lesiones, box scores o líneas no rompe el resto.

## Corte, muestra y referencias

- Solo partidos REG terminados y fechados **antes** de `matchup.before`, dentro de
  la temporada seleccionada. Se excluye íntegramente el día del matchup; esto es
  más conservador que inferir qué resultado ya estaba disponible ese mismo día.
- Se respeta la ventana existente (por defecto últimos cinco). Se necesitan al
  menos tres partidos por equipo. Una ventana de un partido puede explorarse,
  pero no produce un candidato. No se rellena el inicio de temporada con ceros.
- Splits local/visitante: mínimo dos partidos por equipo en esa condición; se
  omiten en sede neutral o al comparar equipos sin local definido.
- H2H: como máximo cinco encuentros REG de las últimas tres temporadas incluyendo
  la actual, anteriores al corte. Mínimo tres; su peso es pequeño.
- Referencia de liga: promedio de puntos por equipo de los partidos REG finalizados
  de esa temporada **anteriores al corte**, con mínimo 16 partidos de liga.
  Para Game Total se duplica ese promedio. No es una línea de mercado.
- Lesiones del día de corte y sin fecha se excluyen del contexto del nuevo motor.
  Informes disponibles no equivalen a un archivo completo de lesiones pregame;
  su ausencia tampoco demuestra que el equipo esté sano.

La información histórica puede contener revisiones del proveedor. El filtro por
fecha previene utilizar partidos futuros, pero no reconstruye versiones archivadas
de cada dataset. Los reportes almacenan IDs, valores, pesos y corte para auditar.

## Referencias de puntos y mercados

Para cada equipo: `(PF propios + PA del rival) / 2`. Si hay suficientes splits,
se mezcla 75% de esta referencia reciente y 25% de la referencia calculada del
local en casa y el visitante fuera. Son estimaciones heurísticas sin calibrar;
no son líneas, pronósticos garantizados ni números que se inserten como picks.

| Mercado | Evidencia y comparación sin línea |
| --- | --- |
| Moneyline | Diferencias A − B de margen, PF, récord, tendencia, último partido, net yards/play; PA invertida; H2H y splits. Devuelve equipo lean. |
| Spread | Referencias de margen derivadas de PF, PA, split, H2H y último partido frente a cero. Devuelve solo `equipo side`; no afirma cobertura. |
| Game Total | Sumas PF de ambos, sumas PA de ambos, split, H2H y total del último partido de ambos frente al promedio NFL previo de puntos combinados. |
| Team Total | PF propios, PA rival, split, H2H y último partido frente al promedio NFL previo por equipo. Devuelve tendencia Over/Under respecto a esa referencia. |

En cada mercado de puntos, la dirección del score debe coincidir con la referencia
combinada de puntos y separarse al menos dos puntos de su comparador. Esto es un
filtro heurístico configurable, no evidencia de rentabilidad.

## Pick Score: índice de 0 a 100, nunca porcentaje

Para un factor disponible:

```text
strength_i = clip((valor_i − referencia_i) / escala_i, −1, +1)
contribution_i = 100 × weight_i × strength_i / sum(all_planned_weights)
                 × min(1, min(partidos_A, partidos_B) / 5)
signed_score = sum(contribution_i)
Pick Score = abs(signed_score)
```

El denominador **incluye los pesos de factores faltantes**; no se aumenta la
confianza al perder datos. Sus valores/contribuciones quedan en `None`, no en
cero. La cobertura y las contribuciones a favor/en contra se muestran por separado.
Los ceros medidos son evidencia neutral.

Parámetros iniciales, explícitos y **no ajustados ni validados históricamente**,
en `analysis/pick_config.py`:

- Moneyline: margen 1; PF y PA 0,5 cada uno; récord 0,75; split 0,5; H2H 0,25;
  último partido 0,25; tendencia de margen 0,5; eficiencia neta 0,5.
- Mercados de puntos: anotación 1; puntos permitidos 1; split 0,5; H2H 0,25;
  último partido 0,25.
- Escalas: margen 14 puntos; puntos de equipo 7; total 14; win percentage 0,5;
  yardas netas por jugada 2. La tendencia compara los últimos tres márgenes con
  los anteriores de la ventana (al menos dos).
- Mínimo tres factores disponibles, tres partidos por equipo y score 20/100.
  Un equilibrio o falta de muestra produce «Sin señal fuerte»/«Muestra insuficiente».

Estas elecciones impiden que un solo juego o un H2H corto domine por defecto,
pero no eliminan correlación entre PF, PA y margen. La puntuación no representa
incertidumbre estimada, acierto esperado ni porcentaje calibrado. Ordenar mercados
por este índice prioriza revisión; no compara retornos. Los mercados no son
independientes y no deben combinarse como probabilidades de un parlay.

## Frontera de líneas futuras

`MarketLine` exige ID de partido, mercado, fuente y timestamp con zona horaria.
Un spread es el handicap **con signo aplicado al equipo de la cotización**.
Los totales deben ser positivos; la moneyline usa precio decimal >1. Se rechazan
NaN/inf, eventos/equipos ajenos, cotizaciones duplicadas y observaciones del día
de corte o posteriores (comparación conservadora en UTC).

`analyze_picks(..., lines=())` no obtiene líneas. El adaptador que en el futuro
entregue una cotización deberá verificar autenticidad, vigencia y procedencia;
la validación estructural no demuestra por sí sola que existe en un mercado.
La app actual no introduce líneas manuales ni construye líneas sintéticas.

Con una línea válida, las referencias se comparan con ella y el resultado se
identifica como **candidato con línea**. Un equipo fuerte puede no cubrir una
línea alta. Una cotización ML para el equipo opuesto no se transforma en un precio
inventado para el lean. `probability` y `price_edge` siguen siendo `None`: esta
versión no calcula probabilidad calibrada ni valor esperado, aun con precio real.

Para ampliar mercados se añaden generadores de factores/evaluadores en análisis;
no se modifica el acceso a nflreadpy ni se trasladan cálculos a la UI.

## Reproducción y futura validación

```bash
uv run pytest
uv run python scripts/analyze_picks.py --season 2024 --game-id 2024_14_BUF_LA --output .cache/picks-2024-14.json
```

El script usa el mismo servicio que el dashboard y no sobrescribe un reporte
existente. Guarda configuración, versión, fechas, IDs, referencias, contribuciones,
ranking y resultado retrospectivo. `settle_report` compara un snapshot congelado
con el marcador: favor/en contra/push. Un empate no se cuenta como acierto.
Sin líneas, los totales se evalúan contra la referencia estadística almacenada
y el spread únicamente como preferencia de lado; **no son resultados de apuestas
Over/Under o ATS de mercado**. No se reporta ROI ni se calibra un porcentaje.

Antes de reinterpretar el índice como probabilidad, harán falta snapshots de
líneas fechadas, walk-forward, evaluación por mercado, tamaños de muestra y
calibración fuera de muestra. La infraestructura probabilística previa no valida
automáticamente estas nuevas reglas.

## Comprobación funcional con datos reales

Se ejecutó el reporte para `2024_14_BUF_LA`, corte anterior al 8 de diciembre
de 2024: cinco partidos por equipo y 196 resultados previos para la referencia
de liga. Produjo BUF Moneyline lean (65,9/100), BUF side (43,1/100), ninguna señal
fuerte de Game Total, LA Under tendency (40,9/100) y BUF Over tendency (38,3/100).
No se introdujo ninguna línea. El resultado real fue LA 44–BUF 42: el lean de
ganador fue incorrecto. Esta ejecución demuestra integración y liquidación,
**no valida capacidad predictiva ni significa 65,9% de probabilidad**.
