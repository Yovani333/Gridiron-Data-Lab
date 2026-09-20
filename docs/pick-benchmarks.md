# Benchmarks y rangos del Pick Score

Evaluación `paired_benchmarks_v1`; reglas `statistical_leans_v0_2` sin cambios
de pesos, escalas, umbral ni selección de factores.

## Comparación justa

Para Moneyline y preferencia de lado de Spread se comparan tres reglas fijas:
elegir local administrativo, mejor porcentaje de victorias reciente y mejor
margen reciente. Las dos últimas usan la MISMA ventana que el scoring (cinco
partidos en el reporte publicado); si empatan, eligen local. La localía en
neutral es una convención del benchmark, no una ventaja asignada por el modelo.

Para totales se usan siempre Over y siempre Under respecto a la referencia
estadística anterior al partido del mismo candidato. No hay línea de sportsbook,
ATS, cuota, retorno ni probabilidad implícita.

Solo entran candidatos emitidos por el scoring. Las abstenciones se cuentan
aparte. Empates y benchmarks no disponibles se excluyen de AMBOS denominadores.
Se registran oportunidades, emitidos, pares evaluables y resultados discordantes:
solo scoring acierta y solo benchmark acierta. La diferencia en puntos
porcentuales se calcula sobre esos mismos pares, no sobre poblaciones distintas.
Esto evalúa dirección condicional a la selección; no demuestra que el mecanismo
de abstención sea óptimo. Team Total tiene dos candidatos por encuentro.

## Rangos

Bandas [0,20), [20,40), [40,60), [60,80), [80,100], separadas por temporada y
mercado. Nunca interpretar 60/100 como 60% de probabilidad. Se incluyen rangos
vacíos y muestras pequeñas; no se fusionan tras observar resultados.

Se muestran intervalos Wilson 95% descriptivos de la tasa observada y una bandera
de muestra menor a 30 resultados resueltos. Ese umbral es informativo, no una
garantía estadística. Los intervalos asumen observaciones binomiales independientes:
la repetición de equipos y los dos Team Totals del mismo juego incumplen esa
idealización. No son una prueba formal de superioridad ni intervalos de la
diferencia pareada. No se efectuaron pruebas múltiples ni ajustes de parámetros.

Estas temporadas ya eran conocidas durante desarrollo. La evaluación sigue
siendo retrospectiva con datos revisados, no un holdout independiente ni prueba
de rendimiento futuro. La calibración probabilística no se infiere de estos rangos.

## Reproducción

```bash
uv run python scripts/evaluate_picks.py --seasons 2024 2025 --games 5 --output .cache/new-benchmark-report.json --diagnostics-output .cache/new-benchmark-summary.json
```

Ambos destinos deben ser nuevos y distintos. Se conservan huellas de datasets,
configuración, fechas, IDs de partidos usados, direcciones de benchmark y outcomes.
La interfaz Datos usa `config/picks_v0_2_benchmarks.json`, conservando el diagnóstico
v0.2 anterior y el logístico v0.1 como artefactos independientes.

## Resultados ejecutados: 2024–2025

544 partidos REG; selecciones y scores idénticos al reporte anterior (verificación
registro por registro, excluyendo los nuevos campos de benchmark). No se cambiaron pesos.

Moneyline, únicamente los mismos candidatos resueltos, excluyendo un empate en 2025:

| Temporada | N | Scoring | Mejor margen reciente | Mejor récord reciente | Siempre local |
|---|---:|---:|---:|---:|---:|
| 2024 | 153 | 73,86% | 73,20% | 72,55% | 56,21% |
| 2025 | 147 | 68,71% | 69,39% | 70,07% | 53,06% |

Frente al margen reciente, scoring solo difiere en un acierto adicional en 2024
y uno menos en 2025. No demuestra mejora consistente sobre las reglas simples.
El benchmark de local sí queda por debajo, pero eso no basta para justificar
la complejidad adicional del motor.

| Score Moneyline | 2024: tasa / N resuelto | 2025: tasa / N resuelto |
|---|---:|---:|
| 20–40 | 74,47% / 47 | 53,19% / 47 |
| 40–60 | 71,70% / 53 | 71,79% / 39 |
| 60–80 | 71,79% / 39 | 75,56% / 45 |
| 80–100 | 85,71% / 14 | 87,50% / 16 |

No hay gradiente monotónico estable en ambas temporadas. El rango superior
es pequeño: intervalos Wilson aproximados 60,1–96,0% y 64,0–96,5%, sujetos
a las limitaciones de independencia indicadas. No autoriza etiquetar confianza alta.

Spread sin línea toma exactamente las mismas direcciones que mejor margen en
los 125 candidatos emitidos de cada temporada: 72,8% y 70,4% de ganador, no ATS.
Game Total: 55,43% (92) en 2024, igual que siempre Over; 59,78% (92) en 2025,
frente a 54,35% siempre Under y 45,65% siempre Over.
Team Total: 70,39% (233) y 65,40% (237), por encima de ambos benchmarks
constantes, pero frente a una media de liga, NO frente a líneas reales.

Próximo paso: mantener parámetros congelados y registrar decisiones prospectivas;
después estudiar redundancia mediante ablaciones predefinidas. No optimizar pesos
sobre estos mismos resultados y presentarlos como validación independiente.
