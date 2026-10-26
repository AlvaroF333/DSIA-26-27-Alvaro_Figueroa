"""API mínima E2E: recibe texto, opcionalmente lo resume con un proveedor mock/IA."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from flask import Flask, jsonify, request

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("dsia.api")

app = Flask(__name__)


def summarize(text: str) -> str:
    """Resumen naive / mock. Sustituye por cliente OpenAI/Anthropic/HF."""
    text = text.strip()
    if not text:
        raise ValueError("text must be non-empty")
    words = text.split()
    if len(words) <= 12:
        return text
    return " ".join(words[:12]) + "…"


@app.get("/health")
def health():
    return jsonify({"status": "ok", "ts": datetime.now(timezone.utc).isoformat()})


@app.post("/analyze")
def analyze():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "field 'text' is required"}), 400
    try:
        summary = summarize(text)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    logger.info("analyze_ok chars=%s", len(text))
    return jsonify({"summary": summary, "provider": "mock"})


if __name__ == "__main__":
    app.run(debug=True, port=8000)
