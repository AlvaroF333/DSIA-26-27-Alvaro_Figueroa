# Proyecto II — Automatización e integración de servicios (20 %)

**Temas:** 2, 3 y 4  
**Trabajo continuo:** octubre 2026  
**Hito de presentación del Trabajo Final (enunciado E2E):** 19 de octubre de 2026  
**Material de APIs:** [`../../3_automatizacion_e_ia/02_apis_ia.md`](../../3_automatizacion_e_ia/02_apis_ia.md) (B6 Hugging Face) · E5 [`../../3_automatizacion_e_ia/ejercicios/E5_apis_ia.md`](../../3_automatizacion_e_ia/ejercicios/E5_apis_ia.md)

## Relación con el Proyecto III

El Proyecto II **es la base del Proyecto III (Trabajo Final)**.

- Eliges **ya** el dominio, los datos y el problema que llevarás al E2E.
- El repo, el pipeline, el modelo sklearn, los tests y el cliente de IA/HF de esta entrega **se reutilizan y se amplían** en el Proyecto III (API/app, despliegue, monitorización, RC y exposición).
- No se parte de cero en noviembre: el III continúa este mismo trabajo.

```text
Proyecto II (base)                         Proyecto III (ampliación)
─────────────────                          ────────────────────────
datos + pipeline + logs               →    + API / app
modelo sklearn entrenado + inferencia →    + endpoint de predicción (o integrado)
cliente HF / IA (mock + real)         →    + contrato /analyze (o equivalente)
pytest + .env.example (HF_TOKEN)      →    + CI + robustez
README / AI_USAGE                     →    + despliegue + monitorización + exposición
```

## Objetivo

Automatizar un proceso de datos que combine **dos piezas distintas**:

1. un **modelo clásico de scikit-learn** entrenado e integrado en el pipeline (predicción local sobre *tus* datos), y  
2. al menos un **modelo del Hub de Hugging Face vía Inference API** (u otro proveedor API documentado),

con pruebas y buenas prácticas de entornos, **dejando el código listo para crecer hacia el E2E**.

Hugging Face **no es solo LLM**: el mismo `InferenceClient` sirve chat, clasificación de texto, NER, embeddings, traducción, audio, visión, etc. Eliges la **tarea** y el **modelo** (`owner/name`) que aporten al dominio. El demo de aula usa chat por simplicidad; en el proyecto puedes usar cualquier task (guía B6.2).

| Pieza | Rol | No confundir con |
| --- | --- | --- |
| **sklearn** | Clasificación / regresión que **tú entrenas**; `joblib` + inferencia en el job | Un modelo del Hub |
| **Hugging Face** | Modelo(s) del Hub vía API (**cualquier tarea**: LLM, sentiment, embeddings, visión…) | Sustituir el entrenamiento sklearn |

## Requisitos mínimos

1. **Elección de dominio y datos para tu Proyecto III** (documentada en el README: origen, licencia, motivación).
2. Pipeline reproducible (CLI o job) con logs.
3. **Entrenamiento de un modelo scikit-learn** (clasificación, regresión o similar) adecuado al dataset:
   - script o módulo de entrenamiento reproducible (`train` / equivalente);
   - persistencia del modelo (`joblib` / `pickle` u otro formato documentado);
   - **inferencia integrada en el pipeline** (no solo un notebook suelto);
   - métricas de evaluación básicas reportadas en README o informe generado (p. ej. accuracy, F1, RMSE…).
4. Tests pytest (unitarios + al menos un test de integración o marcado), incluyendo al menos un test que cubra la **carga/inferencia del modelo sklearn** (puede usar un fixture o modelo pequeño).
5. **Cliente de borde Hugging Face (u otro API de modelos)** con:
   - modo **`mock`** (obligatorio en tests/CI);
   - proveedor real documentado — **recomendado: Hugging Face** (`HF_TOKEN`, tarea Inference, modelo `owner/name`);
   - la tarea puede ser **chat/LLM u otra** (clasificación, embeddings, visión…); documenta *cuál* y *para qué*;
   - si no hay token aún: `mock` + diseño listo (cliente tipado + `.env.example` con `HF_TOKEN=`).
6. `.env.example` (con `HF_TOKEN=`) y `requirements.txt` (incluye `scikit-learn` y, si usas HF, `huggingface_hub`).
7. Sección `AI_USAGE.md` (proveedor, **tarea**, **modelo Hub** si aplica, qué aceptaste).
8. Estructura modular que permita añadir después API y despliegue **sin reescribir** el núcleo.

### Hugging Face en el Proyecto II (orientación)

```bash
# Token: https://huggingface.co/settings/tokens
# En .env (nunca en Git):
HF_TOKEN=hf_...
```

Ejemplos de encaje (elige el que tenga sentido en tu dominio):

| Idea de producto | Task HF | Encaje con sklearn |
| --- | --- | --- |
| Explicar la predicción al usuario | `chat_completion` | Post-proceso del score sklearn |
| Sentimiento / toxicidad de un texto | `text_classification` | Feature o filtro antes/después del modelo |
| Embeddings para similitud | `feature_extraction` | Enriquecer filas; sklearn usa vectores |
| Etiquetar imágenes del dataset | `image_classification` | Etiqueta auxiliar en el pipeline |

Documenta en el README del repo:

- **tarea** Inference + id del modelo del Hub;
- para qué lo usas en el flujo;
- que en CI corre `mock`.

Referencia de aula: guía **B6** y demo [`ai_api_client.py`](../../3_automatizacion_e_ia/ejemplos/ai_api_client.py) (chat). OpenAI/Anthropic son alternativas válidas sobre todo para texto generativo; el contrato del cliente debe ser el mismo (borde tipado + mock).

## Entrega

- Repo GitHub **del Trabajo Final** (el mismo que usarás en el Proyecto III).
- Historial de commits a lo largo de octubre.
- Artefactos del modelo sklearn versionados con criterio (modelo entrenado y/o instrucciones claras para reentrenar).
- README que deje claro: datos → entrenamiento sklearn → pipeline con inferencia → **borde HF/API (tarea + modelo)** → qué se ampliará en el III.

## Rúbrica orientativa

| Criterio | Peso |
| --- | --- |
| Pipeline y automatización | 20 % |
| Modelo sklearn (entrenamiento + integración) | 20 % |
| Integración API / HF (mock + modelo Hub, cualquier tarea documentada) | 20 % |
| Tests y calidad | 15 % |
| Robustez (errores, logs, config) | 10 % |
| Documentación, citación IA y continuidad hacia el III | 15 % |
