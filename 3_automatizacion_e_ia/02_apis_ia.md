# Sesión 19 oct 2026 — APIs (datos abiertos → IA)

| Recurso | Fichero |
| --- | --- |
| Demo APIs abiertas (HTTP) | [`ejemplos/open_api_client.py`](ejemplos/open_api_client.py) |
| Demo cliente IA | [`ejemplos/ai_api_client.py`](ejemplos/ai_api_client.py) |
| Ejercicio de clase | [`ejercicios/E5_apis_ia.md`](ejercicios/E5_apis_ia.md) |
| Variables de entorno (ejemplo) | [`.env.example`](../.env.example) |
| Base previa (data flows) | [`01_data_flows.md`](01_data_flows.md) |

Este documento es la **referencia amplia** de la sesión de APIs en DSIA:

1. primero un **borde HTTP con APIs abiertas** (meteo, país, festivos, FX…): ves JSON, timeouts y status codes sin pagar ni registrar clave;
2. después **transferimos el mismo patrón** a un cliente multi-proveedor de **LLM** (`complete` + `AIResponse` + secretos + `mock`).

Los **tres conceptos clave** valen para ambos. El E5 practica el borde IA; el Proyecto II puede usar cualquiera de los dos bordes (o los dos).

---

## 0. Objetivos de aprendizaje

### Obligatorios (los 3 conceptos clave)

Al terminar la sesión **debes** ser capaz de:

1. Usar un **cliente de borde** que normaliza la respuesta (`APIResult` en HTTP abierto; `AIResponse` en LLM) sin mezclar el vendor en `transform`.
2. Tratar **errores y timeouts** con criterio: 401/403 ≠ 429 ≠ 5xx; timeout siempre; fallar tipado (`OpenAPIError` / `AIClientError`).
3. Gestionar **secretos** con `.env` / `.env.example` y desarrollar/CI en modo **`mock`** cuando la API pida clave (sobre todo LLM).

### Deseables (material suplementario)

4. Lanzar varias demos de `open_api_client.py` (meteo, país, festivos, FX…).
5. Lanzar el demo IA con **`hf` (Hugging Face)** u otro proveedor si hay token/clave (opcional en aula).
6. Extender el CLI IA con batch JSONL + retries ([`E5`](ejercicios/E5_apis_ia.md)).
7. Documentar uso de IA en `AI_USAGE.md` y encajar cualquier API como **borde** del pipeline.

---

## 1. Por qué esta sesión importa en DSIA

### 1.1 Qué entregamos

En DSIA no entregamos “un notebook que llama a ChatGPT con la clave pegada” ni “un `requests.get` suelto dentro de `transform`”. Entregamos un **borde de aplicación** que otra persona (o CI) pueda:

1. configurar sin tocar código de negocio,
2. ejecutar sin red cuando haga falta (`mock` / fixtures HTTP),
3. cambiar de proveedor o de API sin reescribir el pipeline,
4. **fallar de forma controlada** (error tipado, retries con criterio).

### 1.2 Por qué empezar por APIs abiertas

| Con APIs abiertas aprendes… | Luego en LLM reutilizas… |
| --- | --- |
| URL + params + JSON | SDK detrás de un cliente |
| `timeout`, 404/429/5xx | misma tabla de errores |
| Normalizar a `APIResult` | normalizar a `AIResponse` |
| Casi nunca hay clave | `.env` + `mock` (clave sí) |

Empezar por OpenAI es más caro cognitivamente (SDK, cuota, secreto) y oculta el HTTP. Empezar por Open-Meteo hace visible el borde; el LLM es el **mismo diseño** con secretos.

### 1.3 Mapa mental del semestre

```text
Tema 1  →  pandas + arquitectura (etapas y módulos)
Tema 2  →  pytest + CI (confianza)
Tema 3  →  data flows + APIs (hoy)   ← primero HTTP abierto, luego borde IA
Tema 4  →  asistentes / refactor con IA
Tema 5  →  E2E / deploy
```

El data flow de la sesión anterior es el **centro**. Cualquier API (abierta o LLM) es otro **borde** (como `load`/`save`): Strategy + mock, no lógica de negocio mezclada.

### 1.4 Analogías útiles

| Concepto | Analogía |
| --- | --- |
| Cliente unificado | Mandos universales: mismo botón, distintas TVs |
| `APIResult` / `AIResponse` | Ticket estándar (da igual el mostrador) |
| API abierta (meteo…) | Mostrador público; a menudo sin llave |
| Proveedor LLM (`hf` / `openai` / …) | Mostrador (HF con créditos free; OpenAI de pago) |
| Modo `mock` | Simulador de vuelo: practicas sin avión real |
| `.env` | Caja fuerte; el código solo pide la llave |
| Retry / backoff | Llamar otra vez si la línea está saturada |
| 401/403 | Llave incorrecta: no sirve llamar 10 veces |
| `AI_USAGE.md` | Recibo de qué IA usaste y qué aceptaste |

### 1.5 Regla de oro

> **Primero el borde HTTP (contrato + errores). Si hace falta clave: secretos fuera del código y mock en CI. Reintenta solo lo transitorio.**

---

# PARTE A — Tres conceptos clave (obligatorio)

> Prioridad de clase: **A1 (HTTP abierto) → A2 (errores) → A3 (LLM + secretos/mock)**. El resto del documento es red de seguridad y profundidad.

---

## A1. Concepto clave 1 — Cliente unificado + respuesta normalizada

### Qué es (primero con APIs abiertas)

Un **cliente de borde** es una función (o módulo) que:

1. recibe parámetros de negocio (`lat`/`lon`, código de país, …),
2. habla con la API externa (`requests` / SDK),
3. devuelve **siempre** la misma forma: aquí `APIResult(source, data)`.

```text
Tu aplicación ──► weather_forecast(lat, lon) ──► Open-Meteo (HTTP)
                         │
                         └─► APIResult(source="open-meteo", data={...})
```

### Demo del curso (abrir la sesión aquí)

```bash
cd 3_automatizacion_e_ia/ejemplos
python open_api_client.py weather --lat 40.4168 --lon -3.7038
python open_api_client.py country --code ES
python open_api_client.py fx --base EUR --symbols USD,GBP
```

```python
from dataclasses import dataclass
from typing import Any


@dataclass
class APIResult:
    source: str
    data: dict[str, Any]


def weather_forecast(lat: float, lon: float) -> APIResult:
    # requests.get(..., timeout=15) → JSON → campos normalizados
    return APIResult(source="open-meteo", data={"temperature_c": ..., "wind_kmh": ...})
```

Salida esperada: JSON con `source` + `data` (no el payload crudo del vendor esparcido por el repo).

### El mismo patrón, después, para LLM

Cuando pases a IA, **no inventes otro diseño**: cambias el contrato de salida (`AIResponse`) y el “mostrador” (`mock|openai|anthropic|hf`).

```text
Tu aplicación ──► complete(provider, prompt) ──► Proveedor (mock|openai|…)
                      │
                      └─► AIResponse(provider, text)
```

```bash
python ai_api_client.py --provider mock --prompt "Resume Clean Code en 3 bullets"
```

### Por qué importa en DSIA

Tu pipeline / Proyecto II debe poder cambiar de API o de proveedor **sin** reescribir `transform` ni los tests. El borde cambia; el contrato se mantiene.

### Checklist del concepto 1

- [ ] Sé lanzar al menos `weather` (y otro comando) de `open_api_client.py`
- [ ] Sé explicar qué campos tiene `APIResult` y por analogía `AIResponse`
- [ ] Sé decir por qué no llamamos a `requests` / al SDK desde dentro de `transform`

---

## A2. Concepto clave 2 — Errores, timeouts y reintentos

### Qué es (se ve mejor en HTTP abierto)

No todos los fallos se tratan igual. En `open_api_client.py` ya mapeamos status → `OpenAPIError`:

| Situación | Estrategia |
| --- | --- |
| Timeout de red | Fallar tipado; reintento **limitado** si el job lo permite |
| 404 | Recurso inexistente; **no** reintentar a ciegas |
| 401 / 403 | Configuración (clave/permisos); **no** reintentar a ciegas |
| 429 | Backoff + jitter (la API te pide esperar) |
| 5xx | Reintento **limitado** + error tipado si agotas |
| JSON inválido / vacío | Validar y fallar explícito |

Regla práctica:

> **Reintenta lo transitorio; no reintentes lo de configuración ni el 404.**

### Mínimo HTTP que debes interiorizar

```python
import requests

r = requests.get(url, params=params, timeout=15)  # timeout siempre
if r.status_code == 429:
    raise OpenAPIError("Rate limit")
r.raise_for_status()
payload = r.json()
```

### Transferencia al borde IA (E5)

Los LLM fallan por las mismas familias (auth, rate limit, 5xx, timeout). En el demo base, los fallos de configuración ya son `AIClientError`. En el **E5** practicas reintentos simulados con `--fail-once`:

```text
intento 1 → fallo transitorio
sleep corto
intento 2 → OK  (o agotar reintentos y propagar AIClientError)
```

### Por qué importa en DSIA

Una API real falla. Si tu job aborta a la primera 503 sin criterio, el pipeline es frágil. Si reintentas un 401 en bucle, quemas tiempo y no arreglas nada.

### Checklist del concepto 2

- [ ] Sé clasificar 401 vs 404 vs 429 vs 5xx / timeout en una frase cada uno
- [ ] Sé por qué `timeout=` es obligatorio en `requests`
- [ ] Sé qué pedirá E5 (`--fail-once` + hasta 2 reintentos) sobre el cliente IA

---

## A3. Concepto clave 3 — Secretos + modo `mock` (sobre todo LLM)

### Por qué este concepto va **después**

Muchas APIs abiertas de aula **no piden clave**. El patrón de cliente + errores ya está claro. Al pasar a LLM (o a GitHub/NASA), aparece un requisito nuevo: **credenciales** y un modo de desarrollo **sin red ni cuota**.

### 3.1 Secretos en el entorno

Las claves **no** van en el código ni en GitHub.

```bash
# Desde la raíz del repo del curso
cp .env.example .env
# Edita .env con tus claves (si las tienes). No lo subas.
```

| Variable | Uso |
| --- | --- |
| `OPENAI_API_KEY` | proveedor `openai` |
| `ANTHROPIC_API_KEY` | proveedor `anthropic` |
| `HF_TOKEN` | proveedor `hf` (token de https://huggingface.co/settings/tokens) |
| `GITHUB_TOKEN` | opcional en `open_api_client` (sube rate limit) |
| `LOG_LEVEL` | logging (opcional) |

El demo IA usa `python-dotenv` + `os.getenv(...)`. Si falta la clave → `AIClientError` claro.

### 3.2 Modo `mock` obligatorio (LLM / CI)

```python
if provider == "mock":
    return AIResponse(provider="mock", text=f"[mock] Recibido: {prompt[:200]}")
```

Úsalo para:

- desarrollo offline,
- CI / Actions (sin secretos de IA en el gate básico),
- demos en aula sin depender de cuota/red.

En APIs abiertas el equivalente es **mockear HTTP** en tests (`responses`, fixtures), no pegar a la red en cada push.

### Checklist de seguridad (mínimo)

1. Claves solo en `.env` / secretos del PaaS / GitHub Secrets.  
2. `.env` en `.gitignore`; existe `.env.example` sin valores reales.  
3. No loguear prompts con PII.  
4. Modo `mock` (o mock HTTP) en CI y en el camino feliz de desarrollo.

### Por qué importa en DSIA

Una clave filtrada en un commit es un incidente. Un test que llama a OpenAI (o a Nominatim en bucle) en cada push es lento, caro y flaky. Mock + env resuelve ambos.

### Checklist del concepto 3

- [ ] Sé copiar `.env.example` → `.env` y explicar por qué `.env` no se versiona
- [ ] Sé correr el cliente IA sin ninguna clave (`--provider mock`)
- [ ] Sé listar las 4 reglas de seguridad de arriba

---

## A4. Mapa mental de los 3 conceptos

```text
1. Cliente + contrato     →  APIResult (HTTP)  y  AIResponse (LLM)
2. Errores / timeouts     →  tipados; reintenta solo lo transitorio
3. Secretos + mock        →  cuando hay clave (LLM); CI sin red
```

Orden de clase:

```text
open_api_client (A1–A2)  →  ai_api_client mock (A3)  →  E5 (batch + retries)
```

Si dominas eso, puedes hacer el E5 y enchufar HTTP o IA al Proyecto II sin ensuciar el núcleo.

**Siguiente paso inmediato en clase (tras A1–A3):** [`ejercicios/E5_apis_ia.md`](ejercicios/E5_apis_ia.md).

---

# PARTE B — Material suplementario

> Úsalo para profundizar, preparar el E5/Proyecto II y resolver dudas. **No** sustituye a A1–A3.
> Orden sugerido: B1 capas → B2 catálogo HTTP → B3 anatomía open → B4 anatomía IA → resto.

---

## B1. Capas del borde (HTTP abierto o IA)

```text
        /\
       / App \           pipeline, CLI, API HTTP
      /--------\
     /  Cliente \        weather_forecast() / complete() / …
    /------------\
   /  Servicio    \      meteo | países | FX | open data | LLM | …
  /----------------\
```

| Capa | Responsabilidad | Ejemplo DSIA |
| --- | --- | --- |
| App / dominio | Reglas de negocio, `transform` | pipeline de ventas |
| Cliente | Contrato estable + secretos + errores | `open_api_client` / `ai_api_client` |
| Servicio externo | Red / SDK | Open-Meteo, World Bank, OpenAI, … |

**Heurística:** la app no arma URLs ni importa el SDK por todo el repo; habla con el **cliente**.

---

## B2. Catálogo de APIs abiertas (aula / Proyecto II)

| API | Para qué | ¿Clave? | Docs |
| --- | --- | --- | --- |
| **Open-Meteo** | Previsión / histórico meteo | No | https://open-meteo.com/ |
| **World Bank** | País, capital, región, income level | No | https://datahelpdesk.worldbank.org/knowledgebase/articles/889392 |
| **Nager.Date** | Festivos públicos por país/año | No | https://date.nager.at/Api |
| **Zippopotam.us** | Código postal → lugar / coords | No | https://api.zippopotam.us/ |
| **Open Library** | Búsqueda de libros | No | https://openlibrary.org/developers/api |
| **Frankfurter** | Tipos de cambio (BCE) | No | https://www.frankfurter.app/ |
| **GitHub REST** | Stars, issues, CI de un repo | Opcional (`GITHUB_TOKEN`) | https://docs.github.com/en/rest |
| **Nominatim (OSM)** | Geocoding (dirección ↔ coords) | No (¡Usage Policy!) | https://nominatim.org/ |
| **datos.gob.es** | Datasets abiertos de España | No / según portal | https://datos.gob.es/ |
| **Eurostat** | Indicadores UE | No | https://ec.europa.eu/eurostat/web/main/data/web-services |
| **CoinGecko** | Precios cripto | No (límites) | https://www.coingecko.com/en/api |
| **NASA Open APIs** | APOD, neo, imagery… | Sí (gratis) | https://api.nasa.gov/ |
| **Stripe / Twilio / SendGrid** | Pagos, SMS, email | Sí (producto) | docs de cada vendor |

> En DSIA prioriza APIs **sin clave** para practicar A1–A2. Las de producto siguen el patrón A3 de secretos.

### Demo completa del curso (no LLM)

```bash
cd 3_automatizacion_e_ia/ejemplos

python open_api_client.py weather --lat 40.4168 --lon -3.7038
python open_api_client.py country --code ES
python open_api_client.py holidays --country ES --year 2026
python open_api_client.py postal --country es --code 28001
python open_api_client.py books --query "clean code"
python open_api_client.py fx --base EUR --symbols USD,GBP
python open_api_client.py github --owner dmartincc --repo dsia-26-27
```

Todas escriben un JSON con `source` + `data` normalizado (`APIResult`).

### Funcionalidades típicas en un producto DSIA

| Función | API de ejemplo | Encaje en el pipeline |
| --- | --- | --- |
| Enriquecer filas | World Bank, FX, meteo, festivos | `load` externo → join en `transform` |
| Geocoding / CP | Nominatim, Zippopotam | Dirección o CP → lat/lon |
| Calendario | Nager.Date | Marcar días no laborables en series |
| Alertas | meteo + umbral | Job cron: si lluvia > X, avisar |
| Metadata repo | GitHub | README / badge / chequeo de estrellas |
| Ingesta open data | datos.gob.es / Eurostat | CSV/JSON → mismo `load/validate/save` |
| Notificaciones | email/SMS (vendor) | Borde final tras el gate de calidad |

### Buenas prácticas HTTP (rápido)

1. Siempre `timeout=` en `requests`/`httpx`.  
2. Identifícate si la API lo pide (`User-Agent` en Nominatim).  
3. Respeta rate limits (429 → backoff; no bucles agresivos).  
4. Cachea respuestas estables (FX del día, metadatos de país).  
5. En CI: **mock**; una smoke opcional marcada `integration` si hay red.

---

## B3. Anatomía del demo `ejemplos/open_api_client.py`

| Pieza | Rol | Concepto |
| --- | --- | --- |
| `APIResult` | Contrato de salida | A1 |
| `OpenAPIError` | Error tipado del borde | A2 |
| `_get_json(...)` | HTTP + mapeo de status | A2 |
| `weather_forecast` / `country_info` / … | Funciones de dominio | A1 |
| `GITHUB_TOKEN` (opcional) | Secreto solo si hace falta | A3 |
| `main` / subcomandos | CLI parametrizable | A1 |

Ejemplo mínimo (Open-Meteo):

```python
import requests

def weather_madrid() -> dict:
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": 40.4168,
            "longitude": -3.7038,
            "current": "temperature_2m,wind_speed_10m",
        },
        timeout=15,
    )
    r.raise_for_status()
    cur = r.json()["current"]
    return {
        "temperature_c": cur["temperature_2m"],
        "wind_kmh": cur["wind_speed_10m"],
    }
```

---

## B4. Anatomía del demo `ejemplos/ai_api_client.py`

Cuando el borde HTTP ya está claro, el cliente IA es la misma idea con proveedores y secretos.

### B4.1 Piezas del código

| Pieza | Rol | Concepto |
| --- | --- | --- |
| `AIResponse` | Contrato de salida (análogo a `APIResult`) | A1 |
| `AIClientError` | Error tipado del borde | A2 |
| `complete(...)` | Strategy por `provider` | A1 |
| `load_dotenv()` / `os.getenv` | Secretos | A3 |
| `main` / `argparse` | CLI | A1 |

Proveedores en el demo:

| `--provider` | SDK / nota | Variable |
| --- | --- | --- |
| `mock` | sin red | ninguna |
| `hf` | `huggingface_hub.InferenceClient` (**recomendado** en DSIA) | `HF_TOKEN` |
| `openai` | `openai.OpenAI` | `OPENAI_API_KEY` |
| `anthropic` | `anthropic.Anthropic` | `ANTHROPIC_API_KEY` |

> En el curso prioriza **Hugging Face** como proveedor real: cuenta gratuita, token gratis, Inference Providers, y eliges **cualquier modelo del Hub** (LLM u otra tarea) por su id. El demo CLI usa chat; el proyecto puede usar clasificación, embeddings, visión, etc. OpenAI/Anthropic son alternativas sobre todo para texto generativo.

### B4.2 Cómo se relacionan con los 3 conceptos

| Acción en el demo | Concepto |
| --- | --- |
| `complete("mock", ...)` → `AIResponse` | A1 |
| Clave ausente → `AIClientError` | A2 + A3 |
| Proveedor desconocido → error claro | A2 |
| CLI `--provider` / `--prompt` | A1 (job parametrizable) |

### B4.3 Componer API abierta + LLM (idea, no obligatorio)

```text
Open-Meteo (datos)  →  resumen estructurado  →  complete(mock|hf)  →  texto para el usuario
        ↑ borde datos                              ↑ borde IA
```

Mantén **dos clientes** (o dos módulos): uno HTTP de datos, otro de LLM. No mezcles `requests` + prompt dentro de `transform`.

### B4.4 Guion de exposición (≈ 30–35 min)

1. Capas B1 + lanzar `open_api_client.py weather` y señalar `APIResult` (A1, 8 min).  
2. Tabla 401/404/429/5xx + `timeout` sobre el mismo cliente (A2, 8 min).  
3. Puente: “mismo patrón, ahora LLM” → demo `mock` + `.env.example` + mención HF (A3, 10 min).  
4. Adelanto E5: batch JSONL + `--fail-once` (5–8 min).

---

## B5. Buenas prácticas de organización

### Nombres y módulos

Patrón recomendado en el Proyecto II:

```text
proyecto/
  pipeline/              # load / transform / save
  integrations/
    open_data_client.py  # meteo / países / FX / …
    ai_client.py         # complete + AIResponse (mock | hf | …)
    prompts.py           # plantillas (opcional)
  tests/
    test_open_data_client.py # mock HTTP
    test_ai_client.py        # mock
.env.example             # incluye HF_TOKEN=
AI_USAGE.md
```

### Reglas prácticas

1. Un solo sitio conoce SDKs / URLs de cada vendor.  
2. El resto importa el cliente (`weather_forecast`, `complete`, …), no `InferenceClient(...)` / `OpenAI(...)` sueltos.  
3. Tests de bordes: **mock** (sin red en CI).  
4. Prompts y queries versionados; no literales mágicos repartidos.  
5. Documenta el **modelo del Hub** (`owner/name`) que usas con HF.

---

## B6. Hugging Face: usar modelos del Hub (no solo LLM)

En DSIA, **Hugging Face es el proveedor real recomendado** para el borde de modelos vía API (sesión, E5 extensión y Proyecto II).

**Importante:** el Hub no es “solo chat/LLM”. Aloja (y sirve por Inference) modelos de **muchas tareas**: LLM/chat, clasificación de texto, NER, embeddings, traducción, speech-to-text, visión, etc. Eliges el modelo por su ficha en el Hub y el método de `InferenceClient` que corresponda a esa tarea.

| Pieza | Qué es | En el curso |
| --- | --- | --- |
| **Modelo sklearn** | Clásico, **entrenado por ti** sobre tus datos; local | `train` + `joblib` + inferencia en el pipeline |
| **Modelo en el Hub (HF)** | Preentrenado (o publicado) **de terceros**; vía API | `InferenceClient` + `HF_TOKEN` + id `owner/name` |

No sustituyen lo mismo: sklearn es *tu* modelo de negocio; HF es un **servicio externo** de modelos (**de cualquier tipo** que elijas).

### B6.1 Cuenta, token y dependencia

1. Crea cuenta en [huggingface.co](https://huggingface.co/).  
2. Token: [Settings → Access Tokens](https://huggingface.co/settings/tokens) (permiso de lectura basta para Inference).  
3. En la raíz del repo:

```bash
cp .env.example .env
# HF_TOKEN=hf_...
pip install huggingface_hub   # o añádelo a requirements.txt
```

Docs oficiales: [Inference guide](https://huggingface.co/docs/huggingface_hub/guides/inference) · [Inference Providers](https://huggingface.co/docs/inference-providers) · [Tasks](https://huggingface.co/tasks).

### B6.2 Tareas ≠ solo chat

`InferenceClient` expone un método por familia de tarea. Ejemplos (orientativos):

| Tarea | Método (idea) | Ejemplo de uso en un producto DSIA |
| --- | --- | --- |
| Chat / LLM | `chat_completion` | Explicar predicciones, resumir informe |
| Text generation | `text_generation` | Completar plantillas |
| Clasificación de texto | `text_classification` | Sentimiento, toxicidad, etiquetas |
| Token classification | `token_classification` | NER (personas, orgs…) |
| Feature extraction | `feature_extraction` | Embeddings para búsqueda / clustering |
| Translation | `translation` | ES ↔ EN en el pipeline |
| ASR | `automatic_speech_recognition` | Audio → texto |
| Vision | `image_classification` / `object_detection` / … | Etiquetar imágenes del dominio |

En el **demo de aula** (`ai_api_client.py --provider hf`) usamos **chat** porque es el camino más simple para practicar `complete` + `AIResponse`. En el **Proyecto II** puedes (y a menudo debes) envolver **otra tarea** del Hub con el mismo criterio de borde: cliente tipado, mock en CI, modelo documentado.

### B6.3 Demo de aula (chat / LLM)

```python
from huggingface_hub import InferenceClient

client = InferenceClient(api_key=os.environ["HF_TOKEN"], provider="auto")
result = client.chat_completion(
    messages=[{"role": "user", "content": prompt}],
    model="mistralai/Mistral-7B-Instruct-v0.3",  # id del Hub
    max_tokens=256,
)
text = result.choices[0].message.content
```

```bash
cd 3_automatizacion_e_ia/ejemplos
python ai_api_client.py --provider hf --prompt "Resume SOLID en 3 viñetas"
python ai_api_client.py --provider hf --model mistralai/Mistral-7B-Instruct-v0.3 \
  --prompt "Explica idempotencia en una frase"
```

Contrato del demo: `AIResponse(provider="huggingface", text=...)`. Si en el proyecto usas otra tarea, define un contrato propio (`APIResult` / dataclass) — misma idea A1.

### B6.4 Ejemplo mínimo de otra tarea (clasificación)

```python
from huggingface_hub import InferenceClient

client = InferenceClient(api_key=os.environ["HF_TOKEN"], provider="auto")
# Elige un modelo de text-classification en el Hub; documenta el id.
labels = client.text_classification(
    "El servicio fue excelente y rápido",
    model="distilbert/distilbert-base-uncased-finetuned-sst-2-english",
)
# → lista de {label, score}; normalízala en tu cliente de borde
```

### B6.5 Elegir modelo

- Id = `organizacion/nombre` en el Hub.  
- Filtra por **task** en [huggingface.co/tasks](https://huggingface.co/tasks) o en la ficha del modelo.  
- Comprueba que tenga Inference / Providers activos; si falla, cambia de modelo.  
- Documenta en README / `AI_USAGE.md`: **tarea + modelo + por qué** (no solo “usé HF”).

### B6.6 Cuota, errores y buenas prácticas

- Cuentas free suelen tener **créditos mensuales** limitados: smoke, no CI.  
- 401 → no reintentar; 429 → backoff; en clase vuelve a `mock`.  
- En CI/tests: **siempre mock** (o fixture) del borde HF.  
- No subas `HF_TOKEN` al repo.

### B6.7 Otros proveedores (opcional, sobre todo LLM)

OpenAI/Anthropic cubren sobre todo chat/completions. Siguen siendo válidos para texto generativo; **no** sustituyen el abanico de tareas del Hub.

```bash
python ai_api_client.py --provider openai --prompt "..."
python ai_api_client.py --provider anthropic --prompt "..."
```

```text
AIClientError: Falta HF_TOKEN en el entorno
AIClientError: Instala: pip install huggingface_hub
```

Eso es **deseable**: fallar explícito > traza opaca.

## B7. Batch JSONL y retries (puente al E5)

El ejercicio de clase pide extender el demo **IA**:

1. `--batch prompts.txt` + `--output respuestas.jsonl` (5 prompts → 5 líneas JSON).  
2. `--fail-once` + hasta 2 reintentos con `sleep` corto.  
3. `AI_USAGE.md` con proveedor + citación.

Formato mínimo de cada línea JSONL:

```json
{"prompt": "...", "provider": "mock", "text": "..."}
```

No hace falta proveedor real para completar E5. Los conceptos A1–A2 ya los practicaste con HTTP abierto; aquí cierras A3 + retries.

---

## B8. `AI_USAGE.md` (citación)

En DSIA documentamos el uso de asistentes/APIs:

```text
# AI usage

- Provider: mock
- Asistente: <ninguno | Cursor / ChatGPT / …>
- Qué aportó: …
- Qué acepté / revisé: …
- Comandos de evidencia: …
```

Objetivo: trazabilidad académica y hábito profesional (qué generó la máquina vs qué validaste tú).

---

## B9. Encaje con el data flow / Proyecto II

```text
load (CSV / API abierta) → validate/transform → (sklearn)
        → borde IA (complete, opcional) → save / metrics / notify
```

### Proyecto II (mínimo razonable)

- Al menos un borde HTTP de datos abiertos **bien hecho**, **o** cliente unificado IA + modo `mock`.  
- Tests de bordes **sin** red.  
- `AI_USAGE.md` si usaste asistentes o APIs de LLM.  
- CI verde sin secretos de pago obligatorios.

La arquitectura (Strategy / borde) existe en gran parte **para poder testear y automatizar**.

---

## B10. Anti-patrones frecuentes (lista negra)

1. API key hardcodeada en `.py` o en el README.  
2. Subir `.env` a GitHub.  
3. Llamar al proveedor real en cada test de CI.  
4. Mezclar descarga HTTP + prompt LLM + pandas en la misma función.  
5. `except: pass` alrededor de la llamada a la API.  
6. Reintentar 401/403 (o 404) en bucle.  
7. Loguear el prompt completo con datos personales.  
8. Acoplar el resto de la app a tipos del SDK (`ChatCompletion`) en vez de `AIResponse`.  
9. Un solo `if provider == "openai"` repartido por todo el repo (sin cliente unificado).  
10. Celebrar “funciona en mi Mac con la clave en el shell” sin `.env.example`.  
11. Llamar Nominatim/OSM en un bucle sin `User-Agent` ni respeto a la política de uso.  
12. Meter `requests.get(...)` dentro de `transform` en lugar de un cliente de borde.  
13. Empezar el diseño por el SDK de OpenAI sin haber cerrado contrato + errores en un HTTP simple.

---

## B11. Ejemplo guiado: de HTTP a LLM

### Paso 1 — contrato HTTP (idea)

```python
from dataclasses import dataclass
from typing import Any


@dataclass
class APIResult:
    source: str
    data: dict[str, Any]
```

### Paso 2 — contrato LLM + mock + retry acotado

```python
import time
from dataclasses import dataclass


@dataclass
class AIResponse:
    provider: str
    text: str


class AIClientError(RuntimeError):
    pass


def complete(provider: str, prompt: str) -> AIResponse:
    if provider == "mock":
        return AIResponse("mock", f"[mock] {prompt[:80]}")
    raise AIClientError(f"Proveedor no soportado en el ejemplo: {provider}")


def complete_with_retries(provider: str, prompt: str, attempts: int = 3) -> AIResponse:
    last: Exception | None = None
    for i in range(attempts):
        try:
            return complete(provider, prompt)
        except AIClientError as exc:
            last = exc
            # Solo reintentaríamos errores transitorios reales (5xx/timeout).
            # En el ejemplo pedagógico, el mock no falla: el E5 simula con --fail-once.
            time.sleep(0.2)
    raise AIClientError(f"Agotados {attempts} intentos") from last
```

### Test (solo mock — sin red)

```python
def test_complete_mock_normaliza_respuesta():
    resp = complete("mock", "Hola DSIA")
    assert resp.provider == "mock"
    assert "Hola" in resp.text


def test_proveedor_desconocido_raises():
    try:
        complete("no-existe", "hola")
        assert False, "debía fallar"
    except AIClientError:
        pass
```

Los tres conceptos aparecen: **contrato** (`AIResponse`, análogo a `APIResult`), **errores tipados**, **mock/secretos** (no hace falta `.env` en mock).

---

## B12. Autoevaluación (clave vs suplementario)

### Clave (debe salir fluido)

1. ¿Qué es un cliente unificado y qué devuelve en HTTP abierto vs en LLM?  
2. ¿Por qué `timeout` y cómo clasificas 401 / 429 / 5xx?  
3. ¿Por qué existe el modo `mock` y dónde viven las claves?  
4. ¿Qué errores se reintentan y cuáles no?

### Suplementario

5. ¿Por qué la IA (u otra API) no va dentro de `transform`?  
6. Nombra 3 APIs abiertas no-LLM y si necesitan clave.  
7. ¿Qué pides en cada línea del JSONL del E5? ¿Para qué sirve `AI_USAGE.md`?

Si fallas en 1–4, rehaz la Parte A: primero `open_api_client`, luego demo `mock`, antes del E5.

---

## B13. Checklist de salida

### Conceptos clave

- [ ] Al menos 2 comandos de `open_api_client.py` lanzados por ti  
- [ ] Sé explicar `APIResult` y, por transferencia, `AIResponse` + `complete`  
- [ ] Sé clasificar 401 / 404 / 429 / 5xx / timeout  
- [ ] Sé aplicar el checklist de secretos / mock  

### Ejercicio / proyecto

- [ ] E5: batch JSONL con 5 registros  
- [ ] E5: retry con `--fail-once`  
- [ ] `AI_USAGE.md` escrito  
- [ ] Idea clara de cómo enchufar un borde HTTP **y/o** IA al Proyecto II  

---

## B14. Para la siguiente sesión / hito

1. Completa E5 en modo `mock`.  
2. No metas claves en el repo del Proyecto II.  
3. Cuando uses asistentes en Tema 4, el mismo criterio de citación (`AI_USAGE.md`) se mantiene.

---

## B15. Apéndice A — Chuleta rápida

```bash
cd 3_automatizacion_e_ia/ejemplos

# 1) APIs abiertas (empezar aquí)
python open_api_client.py weather --lat 40.4168 --lon -3.7038
python open_api_client.py country --code ES
python open_api_client.py holidays --country ES --year 2026
python open_api_client.py postal --country es --code 28001
python open_api_client.py fx --base EUR --symbols USD

# 2) Cliente IA (mock)
python ai_api_client.py --provider mock --prompt "Di hola en una frase"

# 3) Hugging Face (requiere HF_TOKEN en .env)
python ai_api_client.py --provider hf --prompt "Resume SOLID en 3 viñetas"
python ai_api_client.py --provider hf --model mistralai/Mistral-7B-Instruct-v0.3 --prompt "..."

# 4) Tras E5
python ai_api_client.py --provider mock --batch prompts.txt --output respuestas.jsonl
python ai_api_client.py --provider mock --prompt "test" --fail-once
```

```python
from ai_api_client import complete, AIResponse, AIClientError

resp: AIResponse = complete("mock", "Hola")
assert resp.provider == "mock"
assert resp.text.startswith("[mock]")
```

---

## B16. Apéndice B — Glosario corto EN/ES

| EN | ES / nota |
| --- | --- |
| provider | proveedor (OpenAI, Anthropic, HF, mock) |
| API key / token | clave / token de acceso |
| retry / backoff | reintento / espera creciente |
| jitter | aleatoriedad en la espera (evita thundering herd) |
| rate limit (429) | límite de tasa |
| mock | simulacro / doble de prueba |
| secrets | secretos (credenciales) |
| JSONL | JSON Lines (un JSON por línea) |
| open data / open API | datos / API de acceso abierto |
| geocoding | geocodificación (dirección ↔ coordenadas) |
| timeout | tiempo máximo de espera de la petición |

---

## B17. Apéndice C — Preguntas típicas de clase

**¿Por qué no empezamos por OpenAI?**  
Porque el borde HTTP se ve mejor sin SDK ni cuota. Luego el LLM reutiliza el mismo diseño.

**¿Obligatorio pagar OpenAI?**  
No. El modo `mock` basta para E5. Como proveedor real, prioriza **Hugging Face** (`HF_TOKEN` gratis + créditos Inference). OpenAI/Anthropic son opcionales.

**¿Cómo obtengo `HF_TOKEN`?**  
Cuenta en huggingface.co → Settings → Access Tokens → pega el valor en `.env` (nunca en Git).

**¿Puedo usar solo un proveedor en el Proyecto II?**  
Sí: recomendado `mock` + **`hf`**. Deja el cliente unificado; en CI solo mock.

**¿Dónde pongo la clave en GitHub Actions?**  
Settings → Secrets (`HF_TOKEN` si hay smoke real). Para el gate básico del curso, **mock** evita el secreto.

**¿Qué modelo uso en Hugging Face?**  
El que encaje con tu **tarea** (chat, clasificación, embeddings, visión…). En el demo de aula el default es un LLM instruct; en el Proyecto II elige cualquier modelo del Hub con Inference y documenta tarea + id.

**sklearn vs Hugging Face — ¿son lo mismo?**  
No. sklearn = *tu* modelo clásico local (entrenas con tus datos). HF = modelos del Hub vía API (**LLM u otras tareas**). El Proyecto II pide sklearn **y** un borde HF (u otro proveedor API) bien hecho.

**¿HF solo vale para LLM?**  
No. El Hub cubre muchas tasks; el demo usa chat por simplicidad. Ver B6.2.

**¿Por qué `AIClientError` / `OpenAPIError` y no `Exception` genérica?**  
Para que los tests y el CLI puedan distinguir fallos del borde.

**¿El batch JSONL es obligatorio en el Proyecto II?**  
Es el ejercicio de clase (E5). En el proyecto, reutiliza la idea (contratos claros + evidencia) aunque el formato exacto cambie.

**¿Puedo usar solo APIs abiertas y no LLM en el Proyecto II?**  
Sí, si el enunciado lo permite: un buen borde HTTP (meteo, open data, FX…) con tests mock vale como automatización. El cliente IA sigue siendo el foco del E5.

**¿Open-Meteo / World Bank / Nager / Zippopotam requieren registro?**  
No para el uso básico de aula. Lee siempre la licencia y los límites de la API que elijas.

---

## B18. Apéndice D — Mini rúbrica de autocontrol

| Criterio | Insuficiente | Adecuado | Sólido |
| --- | --- | --- | --- |
| Conceptos clave | SDK / `requests` sueltos | Cliente + contrato (`APIResult` o `AIResponse`) | + errores tipados + mock/secretos |
| HTTP abierto | URL pegada en notebook | `open_api_client` o equivalente | + tests mock HTTP |
| Borde HF / IA | Solo notebook ChatGPT | `complete`/`InferenceClient` + `mock` | + tarea + modelo Hub documentados |
| Secretos | Clave en código | `.env` + `.env.example` (`HF_TOKEN`) | + mock en CI |
| Errores | Silenciados / siempre retry | Tabla 401/429/5xx + timeout | + retries con criterio (E5) |
| Proyecto II | API dentro de `transform` | Borde separado | + `AI_USAGE.md` + tests mock |

---

## 25. Cierre

Si dominas la **Parte A**, tienes lo esencial de la sesión:

> **HTTP abierto primero (contrato + errores) → LLM después (mismos bordes + secretos/mock) = borde listo para producto y para CI.**

El material suplementario (catálogo, capas, batch, citación, anti-patrones) te prepara para que ese borde viva en el repo, en el E5 y en el Proyecto II.

**Siguiente paso inmediato:** lanza `open_api_client.py`, luego el demo `mock`, y haz [`ejercicios/E5_apis_ia.md`](ejercicios/E5_apis_ia.md).
