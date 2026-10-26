# E8 — Flujo E2E mínimo (30 min)

**Sesión:** 26 oct 2026  
**Base:** `../plantilla_proyecto/`

## Parte 1 — Levantar plantilla (8 min)

1. Copia `plantilla_proyecto` a tu repo de Proyecto II.
2. Ejecuta `ingest.py` sobre `ventas.csv`.
3. Arranca `app.py` y prueba `/health` + `/analyze` con curl.

## Parte 2 — Enchufar cliente IA (10 min)

Sustituye el resumen naive por `complete(provider="mock", prompt=...)` (importa desde el Tema 3 o copia el módulo).

La respuesta JSON debe incluir `provider`.

## Parte 3 — Contrato (7 min)

- Campo opcional `model` en la respuesta (puede ser `null` en mock).
- Mensaje 400 claro si `text` falta o es vacío.

## Parte 4 — Test (5 min)

Añade test de texto vacío → 400. Suite completa en verde.

## Hecho cuando…

Demo curl funciona y `pytest -q` pasa en tu copia del proyecto.
