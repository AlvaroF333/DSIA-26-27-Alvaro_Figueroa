"""
Cliente HTTP de ejemplo para APIs abiertas (no LLM).

Uso:
    python open_api_client.py weather --lat 40.4168 --lon -3.7038
    python open_api_client.py country --code ES
    python open_api_client.py holidays --country ES --year 2026
    python open_api_client.py postal --country es --code 28001
    python open_api_client.py books --query "clean code"
    python open_api_client.py fx --base EUR --symbols USD,GBP
    python open_api_client.py github --owner dmartincc --repo dsia-26-27

Nota pedagógica: mismas ideas que el cliente IA — borde I/O, errores tipados,
timeouts, y (cuando aplique) secretos en env. Varias de estas APIs no piden clave.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any

import requests

DEFAULT_TIMEOUT = 15


class OpenAPIError(RuntimeError):
    pass


@dataclass
class APIResult:
    source: str
    data: dict[str, Any]


def _get_json(url: str, *, params: dict | None = None, headers: dict | None = None) -> Any:
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.Timeout as exc:
        raise OpenAPIError(f"Timeout al llamar {url}") from exc
    except requests.RequestException as exc:
        raise OpenAPIError(f"Error de red al llamar {url}: {exc}") from exc

    if response.status_code in {401, 403}:
        raise OpenAPIError(f"No autorizado ({response.status_code}): revisa clave/permisos")
    if response.status_code == 404:
        raise OpenAPIError(f"No encontrado (404): {url}")
    if response.status_code == 429:
        raise OpenAPIError("Rate limit (429): espera / reduce frecuencia; no spam")
    if response.status_code >= 500:
        raise OpenAPIError(f"Error del servidor ({response.status_code})")
    if response.status_code >= 400:
        raise OpenAPIError(f"HTTP {response.status_code}: {response.text[:200]}")

    try:
        return response.json()
    except ValueError as exc:
        raise OpenAPIError("La respuesta no es JSON válido") from exc


def weather_forecast(lat: float, lon: float) -> APIResult:
    """Open-Meteo — previsión sin API key. https://open-meteo.com/"""
    payload = _get_json(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto",
        },
    )
    current = payload.get("current", {})
    return APIResult(
        source="open-meteo",
        data={
            "lat": lat,
            "lon": lon,
            "temperature_c": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "wind_kmh": current.get("wind_speed_10m"),
            "weather_code": current.get("weather_code"),
            "time": current.get("time"),
        },
    )


def country_info(code: str) -> APIResult:
    """World Bank — metadatos de país por código ISO2/ISO3. https://datahelpdesk.worldbank.org/knowledgebase/articles/889392"""
    code = code.strip().upper()
    payload = _get_json(
        f"https://api.worldbank.org/v2/country/{code}",
        params={"format": "json"},
    )
    # Respuesta: [meta, [country, ...]]
    if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
        raise OpenAPIError(f"Sin resultados para país: {code}")
    item = payload[1][0]
    return APIResult(
        source="worldbank",
        data={
            "id": item.get("id"),
            "iso2": item.get("iso2Code"),
            "name": item.get("name"),
            "capital": item.get("capitalCity"),
            "region": (item.get("region") or {}).get("value"),
            "income_level": (item.get("incomeLevel") or {}).get("value"),
            "longitude": item.get("longitude"),
            "latitude": item.get("latitude"),
        },
    )


def public_holidays(country: str, year: int) -> APIResult:
    """Nager.Date — festivos públicos por país/año. https://date.nager.at/Api"""
    country = country.strip().upper()
    payload = _get_json(f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country}")
    if not isinstance(payload, list):
        raise OpenAPIError(f"Respuesta inesperada de festivos para {country}/{year}")
    holidays = [
        {
            "date": h.get("date"),
            "name": h.get("name"),
            "local_name": h.get("localName"),
            "global": h.get("global"),
        }
        for h in payload
    ]
    return APIResult(
        source="nager-date",
        data={"country": country, "year": year, "count": len(holidays), "holidays": holidays},
    )


def postal_lookup(country: str, code: str) -> APIResult:
    """Zippopotam.us — código postal → lugar / coords. https://api.zippopotam.us/"""
    country = country.strip().lower()
    code = code.strip()
    payload = _get_json(f"https://api.zippopotam.us/{country}/{code}")
    places = [
        {
            "place": p.get("place name"),
            "state": p.get("state"),
            "latitude": p.get("latitude"),
            "longitude": p.get("longitude"),
        }
        for p in payload.get("places", [])
    ]
    return APIResult(
        source="zippopotam",
        data={
            "country": payload.get("country"),
            "country_abbr": payload.get("country abbreviation"),
            "post_code": payload.get("post code"),
            "places": places,
        },
    )


def books_search(query: str, limit: int = 5) -> APIResult:
    """Open Library — búsqueda de libros sin API key. https://openlibrary.org/developers/api"""
    payload = _get_json(
        "https://openlibrary.org/search.json",
        params={"q": query, "limit": limit},
    )
    docs = payload.get("docs", [])[:limit]
    books = [
        {
            "title": d.get("title"),
            "author": (d.get("author_name") or [None])[0],
            "year": d.get("first_publish_year"),
        }
        for d in docs
    ]
    return APIResult(source="openlibrary", data={"query": query, "count": len(books), "books": books})


def fx_rates(base: str = "EUR", symbols: str = "USD,GBP") -> APIResult:
    """Frankfurter — tipos de cambio (BCE) sin API key. https://www.frankfurter.app/"""
    payload = _get_json(
        "https://api.frankfurter.app/latest",
        params={"from": base.upper(), "to": symbols},
    )
    return APIResult(
        source="frankfurter",
        data={
            "base": payload.get("base"),
            "date": payload.get("date"),
            "rates": payload.get("rates", {}),
        },
    )


def github_repo(owner: str, repo: str) -> APIResult:
    """GitHub REST — metadatos públicos de un repo (rate limit sin token; mejor con GITHUB_TOKEN)."""
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = _get_json(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
    return APIResult(
        source="github",
        data={
            "full_name": payload.get("full_name"),
            "stars": payload.get("stargazers_count"),
            "forks": payload.get("forks_count"),
            "language": payload.get("language"),
            "open_issues": payload.get("open_issues_count"),
            "html_url": payload.get("html_url"),
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Demos de APIs abiertas (no LLM)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_weather = sub.add_parser("weather", help="Open-Meteo forecast")
    p_weather.add_argument("--lat", type=float, default=40.4168)
    p_weather.add_argument("--lon", type=float, default=-3.7038)

    p_country = sub.add_parser("country", help="World Bank country metadata")
    p_country.add_argument("--code", required=True, help="ISO2 o ISO3 (ES, ESP, …)")

    p_holidays = sub.add_parser("holidays", help="Nager.Date public holidays")
    p_holidays.add_argument("--country", default="ES")
    p_holidays.add_argument("--year", type=int, default=2026)

    p_postal = sub.add_parser("postal", help="Zippopotam postal lookup")
    p_postal.add_argument("--country", default="es")
    p_postal.add_argument("--code", required=True)

    p_books = sub.add_parser("books", help="Open Library search")
    p_books.add_argument("--query", required=True)
    p_books.add_argument("--limit", type=int, default=5)

    p_fx = sub.add_parser("fx", help="Frankfurter FX rates")
    p_fx.add_argument("--base", default="EUR")
    p_fx.add_argument("--symbols", default="USD,GBP")

    p_gh = sub.add_parser("github", help="GitHub public repo metadata")
    p_gh.add_argument("--owner", required=True)
    p_gh.add_argument("--repo", required=True)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "weather":
            result = weather_forecast(args.lat, args.lon)
        elif args.cmd == "country":
            result = country_info(args.code)
        elif args.cmd == "holidays":
            result = public_holidays(args.country, args.year)
        elif args.cmd == "postal":
            result = postal_lookup(args.country, args.code)
        elif args.cmd == "books":
            result = books_search(args.query, args.limit)
        elif args.cmd == "fx":
            result = fx_rates(args.base, args.symbols)
        elif args.cmd == "github":
            result = github_repo(args.owner, args.repo)
        else:
            raise OpenAPIError(f"Comando no soportado: {args.cmd}")
    except OpenAPIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
