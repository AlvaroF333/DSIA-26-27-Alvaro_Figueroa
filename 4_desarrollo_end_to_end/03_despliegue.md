# Despliegue y puesta en producción


## Exposición (30 min)

### Empaquetado mínimo

1. `requirements.txt`
2. Runtime Python documentado
3. Comando de arranque (`Procfile` / `startCommand`)
4. `.env.example`
5. `/health` + script de smoke

### Local vs producción

| Local | Producción |
| --- | --- |
| `debug=True` | Gunicorn / uvicorn |
| un proceso | workers |
| `.env` local | secretos del PaaS |

### Release checklist

1. CI verde  
2. Tag semver  
3. Deploy  
4. Smoke `/health` + endpoint crítico  
5. Plan de rollback (tag anterior)

Proveedor de hosting: libre (Render, Fly, Cloud Run…). Se evalúa la **reproducibilidad** y la evidencia.
