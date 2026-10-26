# Sesión 26 oct 2026 — E2E I: arquitectura del flujo completo
 
| Recurso | Fichero |
| --- | --- |
| Demo | [`plantilla_proyecto/`](plantilla_proyecto/) (`ingest.py`, `app.py`, tests) |
| Ejercicio de clase | [`ejercicios/E8_e2e_arquitectura.md`](ejercicios/E8_e2e.md) |
| Datos | [`../3_automatizacion_e_ia/Datos/ventas.csv`](../3_automatizacion_e_ia/Datos/ventas.csv) (~140 válidas / 10 inválidas) |
| Base previa | [`../3_automatizacion_e_ia/`](../3_automatizacion_e_ia/) (sesión 5: job CLI + exit codes + metrics + bash/cron) |
| Enunciado | [`proyectos/proyecto_ii/`](proyectos/proyecto_ii/) |
 
## Historia de la sesión (léela primero)
 
Hoy no aprendes “otra API con Flask/FastAPI”. Aprendes a **conectar todas las piezas** (datos → proceso → IA → API) de forma que otra persona pueda levantarlas, probarlas y verlas funcionar **sin tu ayuda y sin credenciales**:
 
```text
1. Fijas qué entra y qué sale (contratos)     →  Parte A1
2. Cada pieza tiene una frontera clara        →  Parte A2  (ingesta · proceso · IA · API)
3. La IA es un borde sustituible (mock en CI) →  Parte A3
4. Levantas y pruebas la API                  →  Parte B   (/health, /analyze, pytest)
5. Se ve qué pasa y se puede enseñar          →  Parte B   (logs + métricas + demo en 3 comandos)
```
 
**Regla de oro:** si otra persona no puede clonar el repo, ejecutar 3 comandos y ver el flujo completo funcionando **sin claves de API**, **aún no es E2E**.
 
En clase: exposición (~30 min, Parte A + demo) → ejercicio [`E8`](ejercicios/E8_e2e_arquitectura.md) (~50 min, A + B).
 
---
 
## 0. Objetivos
 
### Obligatorios (Parte A)
 
1. Dibujar y justificar la **arquitectura end-to-end**: origen → ingesta/validación → procesamiento → servicio de IA → API propia → logs/métricas.
2. Fijar los **4 contratos del día 1**: schema de entrada, schema de salida de `/analyze`, proveedor IA por defecto y criterio de “demo lista”.
3. Aislar el servicio de IA tras una **interfaz con `mock` por defecto** (CI sin red ni claves).
### Deseables (Parte B)
 
4. Levantar la API y ejercitar `/health` y `/analyze` con `curl`.
5. Escribir tests con `pytest` que cubran contrato, errores y cliente IA mock.
6. Dejar **logs y métricas** útiles y un comando de demo reproducible.
7. Conectar el patrón al **Trabajo Final (Proyecto III)**.
---
 
## 1. Por qué importa en DSIA
 
```text
Tema 1  →  pandas + arquitectura
Tema 2  →  pytest + CI              (confianza en el código)
Tema 3  →  automatizar el flujo     (job CLI, exit codes, cron) + APIs IA
Tema 4  →  E2E (hoy)                (el mismo job crece hasta ser un servicio)
Tema 5  →  deploy                   (lo que hoy corre local, mañana corre en otro sitio)
```
 
Entregamos esto, no una colección de scripts sueltos:
 
```bash
cd 4_desarrollo_end_to_end/plantilla_proyecto
python ingest.py --input ../../3_automatizacion_e_ia/Datos/ventas.csv --output data/clean.csv
python app.py
```
 
| Idea | Analogía |
| --- | --- |
| Flujo E2E | Cadena de montaje completa, de la materia prima al producto en tienda |
| Contrato | Plano de la pieza: si no encaja, no entra |
| Frontera entre capas | Cada máquina hace una cosa y se puede cambiar sin parar la fábrica |
| Mock de IA | Maniquí de pruebas: sirve para ensayar sin gastar el material caro |
| `/health` | Luz de “máquina encendida” |
| `/analyze` | Ventanilla pública: lo único que ve el cliente |
| Logs + métricas | Parte de producción + libro de incidencias |
 
---
 
# PARTE A — Tres conceptos clave
 
> Pregunta guía: ***¿encajan todas las piezas y se pueden probar sin ti?***  
> Orden: **contratos → fronteras → borde IA sustituible**. La operación y los tests vienen en la Parte B.
 
---
 
## A1 — Contratos (lo que fijas el día 1)
 
Un flujo E2E se rompe casi siempre **en las uniones**, no dentro de cada pieza. Por eso lo primero es escribir qué cruza cada unión.
 
```text
[CSV / API origen] ──(1) schema entrada──► ingesta ──► proceso ──► IA ──► API ──(2) schema salida──► cliente
                                                                  │
                                                         (3) proveedor IA
                                    (4) criterio de “demo lista” = lo que verifica cualquiera en 3 comandos
```
 
| # | Contrato | Qué decide | Ejemplo (ajusta al tuyo) |
| --- | --- | --- | --- |
| 1 | **Schema de entrada** | Columnas / JSON obligatorios y sus tipos | `fecha, region, producto, unidades, precio_unitario, cliente_id` |
| 2 | **Schema de salida de `/analyze`** | Campos, tipos y códigos de error | `{"summary": str, "provider": str, "n_chars": int}` |
| 3 | **Proveedor IA por defecto** | Qué se usa si nadie configura nada | `mock` (siempre en CI) |
| 4 | **Criterio de “demo lista”** | Qué 3 comandos demuestran que funciona | `ingest` → `app` → `curl /health` + `/analyze` |
 
Reglas:
 
- El contrato de entrada es el `REQUIRED_COLUMNS` de la sesión 5: si falla, el job termina con exit `2`.
- El contrato de salida se escribe **antes** que la implementación y se comprueba con un test.
- El proveedor por defecto es `mock`; un proveedor real se activa **solo** con configuración explícita (variable de entorno).
- “Demo lista” es una lista de comandos, no una sensación.
**Checklist:** puedo enseñar los 4 contratos en un papel · cualquier cambio de schema se refleja en test · sé qué pasa si falta una columna.
 
---
 
## A2 — Capas y fronteras
 
Cada capa tiene **una responsabilidad** y se comunica con la siguiente solo a través de su contrato.
 
```text
[CSV / API origen]
        │
        ▼
   Ingesta + validación     (ingest.py / pipeline)       ← I/O + contrato de entrada
        │
        ▼
   Procesamiento / features                              ← puro: DataFrame → DataFrame
        │
        ▼
   Servicio de IA (API)     (ai_api_client / mock)       ← borde externo, sustituible
        │
        ▼
   API propia               (/health, /analyze)          ← contrato de salida
        │
        ▼
   Logs + métricas                                       ← transversal: todas las capas
```
 
| Capa | ¿Disco / red? | Cómo se testea |
| --- | --- | --- |
| Ingesta + validación | Disco (lee CSV, escribe `clean.csv`) | `tmp_path` |
| Procesamiento / features | No | DataFrame en memoria |
| Cliente IA | Red (solo el proveedor real) | `mock` determinista |
| API propia | Red local (HTTP) | Cliente de test del framework |
| Logs + métricas | Disco / consola | Comprobar campos del report |
 
Qué **no** debe pasar:
 
- La API **no** parsea CSV ni limpia datos: llama a funciones de las capas inferiores.
- El procesamiento **no** llama a la IA ni escribe ficheros.
- El cliente IA **no** conoce HTTP de tu API ni pandas.
- Mezclar HTTP + LLM + pandas en la misma función → no se puede testear ni sustituir ninguna de las tres cosas.
La ingesta **es** el job de la sesión 5: mismo patrón CLI + `metrics.json` + exit codes. Hoy la salida del job (`data/clean.csv`) pasa a ser la **entrada** del resto del flujo.
 
**Checklist:** nombro las 5 capas y su frontera · sé cuál toca disco/red y cuál no · explico por qué la API no limpia datos.
 
---
 
## A3 — El borde IA: interfaz + mock por defecto
 
La IA es la pieza **más cara, más lenta, menos determinista y con credenciales**. Por eso se aísla tras una interfaz mínima:
 
```text
analyze(text) ──► AIClient (interfaz)
                     ├── MockClient     ← por defecto · determinista · sin red · CI
                     └── RealClient     ← solo si AI_PROVIDER=real y hay clave
```
 
Esquema orientativo:
 
```python
from typing import Protocol
 
class AIClient(Protocol):
    name: str
    def summarize(self, text: str) -> str: ...
 
class MockClient:
    name = "mock"
    def summarize(self, text: str) -> str:
        # Determinista: mismo texto → mismo resultado
        return f"[mock] {text[:60]}…"
 
def get_client() -> AIClient:
    provider = os.getenv("AI_PROVIDER", "mock")   # por defecto: mock
    if provider == "mock":
        return MockClient()
    raise ValueError(f"Proveedor no soportado: {provider}")
```
 
Por qué así:
 
| Decisión | Motivo |
| --- | --- |
| Interfaz mínima (`summarize`) | Cambiar de proveedor no toca la API |
| `mock` determinista | Tests estables y reproducibles |
| Proveedor por variable de entorno | Sin editar código; sin claves en el repo |
| Mock por defecto | `pytest` y CI corren sin red ni secretos |
| Campo `provider` en la respuesta | La demo es honesta: se ve que es mock |
 
**Checklist:** `pytest` pasa sin claves · cambio de proveedor sin tocar `app.py` · no hay claves en el repo.
 
---
 
## A4 — Mapa de los 3 conceptos
 
```text
A1 contratos      →  las piezas encajan
A2 capas/fronteras →  cada pieza se prueba y se cambia por separado
A3 borde IA mock  →  se puede probar todo sin red ni claves
        │
        └── API + tests + logs + demo (Parte B) hacen el flujo operable y enseñable
```
 
**Siguiente paso en clase:** [`ejercicios/E5_e2e_arquitectura.md`](ejercicios/E5_e2e_arquitectura.md).
 
---
 
# PARTE B — Operar y mantener el flujo E2E
 
> La Parte A dice *qué* debe cumplir el flujo.  
> La Parte B enseña *cómo lo levantas y lo pruebas* (ingesta → API → `curl` → `pytest`) y *cómo lo dejas listo para enseñar* (logs, métricas, demo en 3 comandos).
 
---
 
## B1 — Anatomía de la plantilla
 
Ruta: `4_desarrollo_end_to_end/plantilla_proyecto/`
 
| Pieza | Rol | Concepto |
| --- | --- | --- |
| `ingest.py` | CLI: lee CSV, valida, limpia y escribe `data/clean.csv` | Ingesta (sesión 5) |
| Procesamiento / features | Transformaciones puras | Núcleo testeable |
| Cliente IA (`ai_api_client` / mock) | Llama al proveedor o devuelve respuesta simulada | Borde sustituible |
| `app.py` | Expone `/health` y `/analyze` | API propia |
| `tests/` | `pytest` de contrato, errores y mock | Confianza |
 
> Si los nombres exactos de tu plantilla difieren, mantén la **separación de responsabilidades**, no los nombres.
 
---
 
## B2 — Demo en vivo (paso a paso)
 
### 1. Ingesta (reutiliza el job de la sesión 5)
 
```bash
cd 4_desarrollo_end_to_end/plantilla_proyecto
python ingest.py --input ../../3_automatizacion_e_ia/Datos/ventas.csv --output data/clean.csv
echo $?        # 0 → continúa · distinto de 0 → no levantes nada
```
 
### 2. Levantar la API
 
```bash
python app.py  # escucha en http://127.0.0.1:8000
```
 
### 3. Comprobar con `curl` (en otra terminal)
 
```bash
# ¿Está viva?
curl -s http://127.0.0.1:8000/health
 
# Contrato de salida de /analyze
curl -s -X POST http://127.0.0.1:8000/analyze \
  -H 'Content-Type: application/json' \
  -d '{"text":"Texto de ejemplo suficientemente largo para el resumen mock del curso DSIA"}'
```
 
### 4. Tests
 
```bash
pytest -q
```
 
| Qué observar | Por qué |
| --- | --- |
| `/health` responde sin tocar IA ni datos | Debe ser barato y fiable (lo usarán deploy y monitorización) |
| `/analyze` incluye `provider: mock` | La demo no engaña |
| `pytest` pasa sin red | Cliente IA mock por defecto |
 
---
 
## B3 — La API: `/health` y `/analyze`
 
| Endpoint | Método | Función | Debe cumplir |
| --- | --- | --- | --- |
| `/health` | GET | “¿Estoy vivo?” | Respuesta inmediata, sin dependencias externas |
| `/analyze` | POST | Recibe texto, devuelve análisis | Valida entrada, usa el cliente IA, respeta el schema de salida |
 
Códigos de error (consistentes con el exit `1`/`2` de la sesión 5: **distinguir culpa del cliente vs. del sistema**):
 
| Situación | Código HTTP | Equivalente en job |
| --- | --- | --- |
| Entrada inválida (falta `text`, demasiado corto, tipo erróneo) | `400` / `422` | exit `2` (input roto) |
| Proveedor IA caído o con error | `502` / `503` | fallo externo |
| Error inesperado | `500` + log con traza | bug |
 
Reglas:
 
- La **validación** va en la frontera de la API; el resto del código asume datos válidos.
- Nunca devolver trazas ni claves al cliente; sí registrarlas en el log.
- La respuesta tiene **siempre** la misma forma (mismo schema), también al mockear.
---
 
## B4 — Tests del flujo
 
Qué se testea en cada capa:
 
| Capa | Test mínimo |
| --- | --- |
| Procesamiento | DataFrame en memoria → cuenta de filas y columnas esperadas |
| Cliente mock | Determinismo: mismo texto ⇒ misma salida |
| `/health` | `200` + cuerpo esperado |
| `/analyze` (feliz) | `200` + campos del contrato |
| `/analyze` (error) | Entrada inválida ⇒ `400`/`422`, no `500` |
 
Ejemplo (adapta al cliente de test de tu framework):
 
```python
def test_analyze_contract(client):
    r = client.post("/analyze", json={"text": "Texto suficientemente largo para el mock del curso DSIA"})
    assert r.status_code == 200
    body = r.json()
    assert {"summary", "provider", "n_chars"} <= body.keys()
    assert body["provider"] == "mock"
 
def test_analyze_rejects_empty(client):
    r = client.post("/analyze", json={"text": ""})
    assert r.status_code in (400, 422)
```
 
> Test de contrato = si alguien cambia el schema de `/analyze` sin avisar, **falla un test**.
 
---
 
## B5 — Logs y métricas (observabilidad)
 
Qué dejar escrito para poder diagnosticar sin estar delante:
 
| Dónde | Qué registrar |
| --- | --- |
| Ingesta | `rows_in`, `rows_out`, `error_rate` (ya de la sesión 5: `metrics.json`) |
| API | Una línea por petición: endpoint, código, duración |
| Cliente IA | Proveedor usado, duración, error si lo hay (**sin** texto sensible ni claves) |
 
Buenas prácticas:
 
- Usar el módulo `logging`, no `print`.
- Mismo formato de log en todas las capas.
- Los errores externos se registran con contexto (qué proveedor, qué endpoint) y se traducen a un código HTTP limpio.
---
 
## B6 — Criterio de “demo lista” (los 3 comandos)
 
Una demo está lista cuando **un compañero que no ha trabajado contigo** puede hacer esto desde cero y obtener el resultado esperado:
 
```bash
# 1. Preparar datos
python ingest.py --input ../../3_automatizacion_e_ia/Datos/ventas.csv --output data/clean.csv
 
# 2. Levantar la API
python app.py
 
# 3. Verificar (otra terminal)
curl -s http://127.0.0.1:8000/health && pytest -q
```
 
Comprobaciones previas a dar algo por “listo”:
 
- [ ] Funciona en un clon limpio, sin claves ni variables previas.
- [ ] `pytest -q` pasa sin red.
- [ ] El README lista los comandos exactos y el resultado esperado.
- [ ] El proveedor por defecto es `mock` y se indica en la respuesta.
---
 
## B7 — Propiedades (chuleta de diseño)
 
| Propiedad | Pregunta | En la plantilla |
| --- | --- | --- |
| Contrato | ¿Está escrito qué entra y qué sale? | Schema de entrada + schema `/analyze` |
| Separación de capas | ¿Cada pieza hace una sola cosa? | ingesta · proceso · IA · API |
| Sustituibilidad | ¿Cambio el proveedor sin tocar la API? | Interfaz `AIClient` |
| Reproducibilidad | ¿Mismos inputs ⇒ mismos outputs en CI? | Mock determinista |
| Observabilidad | ¿Sé qué pasó? | logs + métricas + códigos HTTP |
| Seguridad básica | ¿Hay secretos en el repo? | Claves solo por entorno |
| Componibilidad | ¿Lo lanza otro (CI, deploy)? | Comandos fijos + `/health` |
 
---
 
## B8 — Puente al Trabajo Final (Proyecto III) y a deploy
 
```text
Sesión 5 (job)      →  ingest.py  (CLI + exit codes + metrics)
Hoy (E2E I)         →  + procesamiento + cliente IA + API + tests + demo
Siguiente (deploy)  →  el mismo flujo, en otro entorno (contenedor / CI / servidor)
```
 
Reutiliza: CLI + exit codes + logs de la sesión 5 · `transform` puro y testeable · `pytest` + CI del Tema 2.  
El día 1 del Trabajo Final fijas los **4 contratos** (A1) y los dejas escritos en el README.
 
---
 
## B9 — Anti-patrones
 
1. Fijar el schema “sobre la marcha”, sin test de contrato.  
2. Lógica de limpieza dentro del endpoint de la API.  
3. Llamar al proveedor de IA directamente desde `app.py`, sin interfaz.  
4. Tests que dependen de red o de claves reales.  
5. Claves de API en el repositorio (o en el historial de git).  
6. `/health` que llama a la IA o lee datos (puede tirar abajo el servicio sin necesidad).  
7. Devolver `500` para entradas inválidas.  
8. Respuesta con forma distinta según proveedor.  
9. Demo que solo funciona en tu portátil (rutas absolutas, venv sin documentar).  
10. “Demo lista” sin lista de comandos reproducible.
---
 
## B10 — Autoevaluación
 
### Clave
 
1. ¿Cuáles son los 4 contratos del día 1 y por qué se fijan antes de programar?  
2. ¿Qué capas tiene el flujo E2E y cuál es la frontera de cada una?  
3. ¿Por qué el proveedor IA por defecto es `mock`?  
4. ¿Qué diferencia hay entre un `400/422` y un `502` en `/analyze`?
### Suplementario
 
5. ¿Por qué `/health` no debe depender de la IA ni de los datos?  
6. ¿Cómo garantizas que un cambio de schema no pasa desapercibido?  
7. ¿Qué parte del job de la sesión 5 reutilizas aquí y cuál es nueva?  
8. ¿Qué tiene que cumplir una demo para considerarse “lista”?
---
 
## B11 — Checklist de salida
 
**Parte A**
 
- [ ] Dibujo la arquitectura y nombro la frontera de cada capa  
- [ ] Tengo escritos los 4 contratos  
- [ ] Cliente IA tras interfaz, `mock` por defecto  
**Parte B**
 
- [ ] Ingesta → API levantada → `curl` a `/health` y `/analyze`  
- [ ] `pytest -q` pasa sin red ni claves  
- [ ] Logs y códigos de error coherentes  
- [ ] Demo en 3 comandos reproducible en un clon limpio  
- [ ] E5 hecho / idea clara para el Trabajo Final  
---
 
## B12 — Apéndices
 
### Chuleta del flujo
 
```bash
cd 4_desarrollo_end_to_end/plantilla_proyecto
 
# Datos
python ingest.py --input ../../3_automatizacion_e_ia/Datos/ventas.csv --output data/clean.csv
echo "exit=$?"
 
# API
python app.py &                       # o en otra terminal
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/analyze \
  -H 'Content-Type: application/json' \
  -d '{"text":"Texto de ejemplo suficientemente largo para el resumen mock del curso DSIA"}'
 
# Tests
pytest -q
```
 
### Glosario
 
| EN / símbolo | Nota |
| --- | --- |
| end-to-end (E2E) | flujo completo de origen a consumidor |
| contract / schema | forma acordada de los datos que cruzan una frontera |
| endpoint | URL + método que expone la API (`/health`, `/analyze`) |
| health check | endpoint barato que indica si el servicio está vivo |
| mock | sustituto determinista de un servicio externo |
| provider | proveedor de IA (real o `mock`) |
| 4xx / 5xx | error del cliente / error del servidor o dependencia |
| environment variable | configuración fuera del código (`AI_PROVIDER`) |
| CI | integración continua: ejecuta tests en cada push/PR |
 
### FAQ
 
**¿Tengo que usar un proveedor de IA real?** No para la demo ni para CI: `mock` por defecto. Uno real es opcional y solo por configuración.  
**¿Qué framework web uso?** El de la plantilla; lo que importa son los contratos y las capas, no el framework.  
**¿Por qué reutilizar la ingesta de la sesión 5?** Porque ya cumple CLI + señales + idempotencia; no se reescribe, se conecta.  
**¿`/health` debe comprobar que la IA responde?** No: mide que el servicio está vivo; comprobar dependencias va aparte.  
**¿Cuándo está “lista” la demo?** Cuando otra persona la reproduce con los 3 comandos en un clon limpio.
 
### Rúbrica
 
| Criterio | Insuficiente | Adecuado | Sólido |
| --- | --- | --- | --- |
| Contratos | Implícitos | Escritos (entrada + salida) | + test de contrato en CI |
| Arquitectura | Todo mezclado | Capas separadas | + fronteras testeadas por capa |
| Borde IA | Llamada directa en la API | Cliente con interfaz | + `mock` por defecto y proveedor por entorno |
| API | Solo `/analyze` | `/health` + `/analyze` | + errores coherentes (4xx vs 5xx) |
| Tests / CI | Ninguno o con red | `pytest` local | `pytest` sin red en CI |
| Demo | Solo en tu máquina | Comandos documentados | 3 comandos en clon limpio |
 
---
 
## Cierre
 
> **Un flujo E2E = contratos escritos + capas con fronteras claras + IA como borde sustituible (mock por defecto), operado con una API testeada y una demo reproducible en 3 comandos.**
 
**Ahora:** [`ejercicios/E5_e2e_arquitectura.md`](ejercicios/E8_e2e.md).