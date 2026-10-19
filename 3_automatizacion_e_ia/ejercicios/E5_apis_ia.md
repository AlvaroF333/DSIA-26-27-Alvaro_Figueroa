# E5 — Bordes de API: abiertas → IA (40 min)

**Sesión:** 19 oct 2026  
**Guía:** [`../02_apis_ia.md`](../02_apis_ia.md) · **HTTP:** [`../ejemplos/open_api_client.py`](../ejemplos/open_api_client.py) · **IA:** [`../ejemplos/ai_api_client.py`](../ejemplos/ai_api_client.py)

## Meta

Practicar el **mismo borde** en dos pasos:

```text
1) API abierta (HTTP + APIResult + errores)
2) LLM (complete + AIResponse + mock + batch/retries)
```

**Núcleo (obligatorio, ~30 min):** Partes 1–5.  
**Cierre (obligatorio, ~5–7 min):** Parte 6 (`AI_USAGE.md`).  
**Extensión (deseable):** Parte 7.

| Guía | Ejercicio |
| --- | --- |
| A1 cliente + contrato | Partes 1 y 3 |
| A2 errores / timeouts | Parte 2 |
| A3 secretos + mock | Partes 3–5 |
| B7 batch / retries | Partes 4–5 |
| B8 citación | Parte 6 |
| B4.3 componer HTTP + LLM | Parte 7 |

Trabaja **sin claves** (HTTP abierto + `mock`). Si tienes cuota, la demo real es opcional y no sustituye al mock.

---

## Parte 1 — A1: smoke de APIs abiertas (8 min)

```bash
cd 3_automatizacion_e_ia/ejemplos

python open_api_client.py weather --lat 40.4168 --lon -3.7038
python open_api_client.py country --code ES
python open_api_client.py fx --base EUR --symbols USD,GBP
```

Elige **un** comando extra (festivos, postal, libros o GitHub):

```bash
python open_api_client.py holidays --country ES --year 2026
# o: postal --country es --code 28001
# o: books --query "clean code"
# o: github --owner dmartincc --repo dsia-26-27
```

Anota en 2–3 líneas:

1. Qué campos trae el JSON (`source` + `data`).  
2. Por qué conviene devolver `APIResult` y no el JSON crudo del vendor dentro de `transform`.  
3. Una frase: *qué API usarías en tu Proyecto II y para enriquecer qué*.

---

## Parte 2 — A2: errores tipados (5 min)

Sin reescribir aún el cliente IA: observa el borde HTTP.

1. Abre `open_api_client.py` y localiza `_get_json` / `OpenAPIError`.  
2. Relaciona cada caso con una estrategia:

| Caso | ¿Reintentar? | Por qué (una frase) |
| --- | --- | --- |
| Timeout | | |
| 404 | | |
| 401 / 403 | | |
| 429 | | |
| 5xx | | |

3. Fuerza un fallo controlado (debe salir `ERROR:` y exit ≠ 0):

```bash
python open_api_client.py postal --country es --code 00000
# o un código de país inventado:
python open_api_client.py country --code ZZ
```

> Regla de la guía: **reintenta lo transitorio; no reintentes configuración ni 404.**

---

## Parte 3 — A3: smoke mock del cliente IA (5 min)

```bash
cd 3_automatizacion_e_ia/ejemplos
python ai_api_client.py --provider mock --prompt "Di hola en una frase"
```

Confirma que imprime algo como `[mock]` + eco del prompt.

Si falla el import de `dotenv`, instala `python-dotenv` en el entorno del curso.

Anota en una línea la analogía: `APIResult(source, data)` ↔ `AIResponse(provider, text)`.

---

## Parte 4 — Batch JSONL (10 min)

Extiende [`ai_api_client.py`](../ejemplos/ai_api_client.py):

1. Crea `prompts.txt` con **5 líneas** (un prompt por línea).  
2. Añade al CLI:
   - `--batch PATH` — lee prompts línea a línea  
   - `--output PATH` — escribe JSONL (una respuesta por línea)  
3. Cada línea del JSONL debe tener al menos:

```json
{"prompt": "...", "provider": "mock", "text": "..."}
```

Uso:

```bash
python ai_api_client.py --provider mock --batch prompts.txt --output respuestas.jsonl
```

> Si pasas `--batch`, `--prompt` deja de ser obligatorio.

Comprueba: `wc -l respuestas.jsonl` → `5`.

---

## Parte 5 — Reintentos (8 min)

1. Añade `--fail-once` (o equivalente interno) que haga fallar la **primera** llamada a `complete` con `AIClientError`.  
2. Envuelve la llamada con hasta **2 reintentos** y un `sleep` corto (p. ej. 0.2 s).  
3. Si agotas los reintentos → propaga `AIClientError`.

Prueba manual:

```bash
python ai_api_client.py --provider mock --prompt "test" --fail-once
# debe recuperar tras el primer fallo y devolver texto mock
```

Conecta con la Parte 2: el `--fail-once` simula un fallo **transitorio** (como un 5xx), no un 401.

---

## Parte 6 — Citación `AI_USAGE.md` (5–7 min)

Crea o actualiza `AI_USAGE.md` (junto al ejemplo o en tu repo de práctica) con:

- Proveedor usado (`mock`; y, si aplica, uno real)
- Si un asistente escribió parte del código: herramienta + qué aceptaste / qué cambiaste
- Comandos de evidencia (HTTP abierto + batch + retry)

Plantilla mínima:

```text
# AI usage

- Provider: mock
- Asistente: <ninguno | Cursor / ChatGPT / …>
- Qué aportó: …
- Qué acepté / revisé: …
- APIs abiertas probadas: weather, country, fx, …
- Comandos:
  python open_api_client.py weather --lat 40.4168 --lon -3.7038
  python ai_api_client.py --provider mock --batch prompts.txt --output respuestas.jsonl
  python ai_api_client.py --provider mock --prompt "test" --fail-once
```

---

## Parte 7 — Extensión (deseable, ~10 min)

Elige **una**:

### 7.1 Componer HTTP + LLM (idea)

Escribe un script corto o función que:

1. llame a `weather_forecast` (o al CLI weather),  
2. arme un prompt con temperatura/viento,  
3. pase ese prompt a `complete("mock", ...)`.

Mantén **dos bordes** (no mezcles `requests` + prompt en la misma función de negocio).

### 7.2 Test sin red

Añade un test mínimo del `complete("mock", ...)` (assert de `provider` y prefijo `[mock]`). No pegues HTTP real en CI.

### 7.3 Demo real (solo si hay clave)

```bash
cp ../../.env.example ../../.env   # raíz del repo, si aún no existe
# Rellena OPENAI_API_KEY (u otra)
python ai_api_client.py --provider openai --prompt "Resume SOLID en 3 viñetas"
```

Documenta en `AI_USAGE.md` el proveedor real. El E5 **sigue** validándose en `mock`.

---

## Hecho cuando…

- [ ] Has lanzado ≥ 3 comandos de `open_api_client.py` y anotado `source`/`data`  
- [ ] Has rellenado la tabla 401/404/429/5xx (Parte 2)  
- [ ] Smoke `mock` OK  
- [ ] `respuestas.jsonl` tiene **5** registros válidos  
- [ ] El retry con `--fail-once` recupera y no cae a la primera  
- [ ] Existe `AI_USAGE.md` con proveedor + citación + comandos  
- [ ] Entiendes por qué el modo `mock` (y el mock HTTP) es obligatorio en CI / desarrollo offline  
