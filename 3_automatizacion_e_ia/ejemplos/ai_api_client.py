"""
Cliente unificado para servicios de IA.

Uso:
    python ai_api_client.py --provider mock --prompt "Hola"
    python ai_api_client.py --provider hf --prompt "Resume SOLID en 3 viñetas"
    python ai_api_client.py --provider hf --model mistralai/Mistral-7B-Instruct-v0.3 --prompt "..."

Proveedor real recomendado: Hugging Face (`HF_TOKEN`). Este demo usa chat/LLM;
en el Proyecto II puedes envolver otras tareas del Hub (clasificación, embeddings…).
OpenAI / Anthropic son opcionales. El modo `mock` permite practicar sin claves.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class AIResponse:
    provider: str
    text: str


class AIClientError(RuntimeError):
    pass


def complete(provider: str, prompt: str, model: str | None = None) -> AIResponse:
    provider = provider.lower().strip()
    if provider == "mock":
        return AIResponse(provider="mock", text=f"[mock] Recibido: {prompt[:200]}")

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise AIClientError("Falta OPENAI_API_KEY en el entorno")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AIClientError("Instala el SDK: pip install openai") from exc
        client = OpenAI(api_key=api_key)
        chosen = model or "gpt-4o-mini"
        result = client.chat.completions.create(
            model=chosen,
            messages=[{"role": "user", "content": prompt}],
        )
        return AIResponse(provider="openai", text=result.choices[0].message.content or "")

    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise AIClientError("Falta ANTHROPIC_API_KEY en el entorno")
        try:
            import anthropic
        except ImportError as exc:
            raise AIClientError("Instala el SDK: pip install anthropic") from exc
        client = anthropic.Anthropic(api_key=api_key)
        chosen = model or "claude-sonnet-4-20250514"
        result = client.messages.create(
            model=chosen,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in result.content if hasattr(block, "text"))
        return AIResponse(provider="anthropic", text=text)

    if provider in {"hf", "huggingface"}:
        token = os.getenv("HF_TOKEN")
        if not token:
            raise AIClientError("Falta HF_TOKEN en el entorno")
        try:
            from huggingface_hub import InferenceClient
        except ImportError as exc:
            raise AIClientError("Instala: pip install huggingface_hub") from exc
        # Inference Providers: token de usuario + modelo del Hub (id owner/name).
        # Docs: https://huggingface.co/docs/huggingface_hub/guides/inference
        client = InferenceClient(api_key=token, provider="auto")
        chosen = model or "mistralai/Mistral-7B-Instruct-v0.3"
        result = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=chosen,
            max_tokens=256,
        )
        text = result.choices[0].message.content or ""
        return AIResponse(provider="huggingface", text=text)

    raise AIClientError(f"Proveedor no soportado: {provider}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="mock", choices=["mock", "openai", "anthropic", "hf"])
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--model", default=None)
    args = parser.parse_args()
    response = complete(args.provider, args.prompt, args.model)
    print(f"[{response.provider}]\n{response.text}")


if __name__ == "__main__":
    main()
