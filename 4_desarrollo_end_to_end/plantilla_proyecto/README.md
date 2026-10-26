# Plantilla de proyecto End-to-End (DSIA)

Esqueleto mínimo para el Trabajo Final.

## Estructura

```text
plantilla_proyecto/
  app.py       # API Flask (/health, /analyze)
  ingest.py    # Limpieza de CSV de ventas
  test_app.py  # Tests básicos
  README.md
```

## Arranque

Desde la raíz del curso (con el venv activado):

```bash
cd 5_desarrollo_end_to_end/plantilla_proyecto
python ingest.py --input ../../3_automatizacion_e_ia/Datos/ventas.csv --output data/clean.csv
python app.py
# en otra terminal:
curl -X POST http://127.0.0.1:8000/analyze -H 'Content-Type: application/json' \
  -d '{"text":"Necesito un resumen breve de este texto de ejemplo para la demo"}'
pytest -q
```

## Qué debes ampliar

- Sustituir el resumen mock por un cliente de IA real (con fallback).
- Añadir autenticación simple o API key si despliegas en público.
- Empaquetar y desplegar (Render u otro).
- Documentar uso de IA en `AI_USAGE.md`.
