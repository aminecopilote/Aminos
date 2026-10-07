"""Free / low-cost OpenAI-compatible LLM providers (source: github.com/mnfst/awesome-free-llm-apis).

Free tiers, limits and model names change often: check the list before relying on a default,
and override with --model. Stdlib only (urllib), no extra dependency.

Confidentiality: only `ollama` (local) keeps documents on your machine. Every other provider
receives the text of the document; some free tiers may use prompts for training. They are
therefore refused unless the caller explicitly accepts it (allow_remote=True / --allow-free-tier).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from .llm import Chat


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    env_key: str          # environment variable holding the API key ("" = no key needed)
    model: str            # default model
    data_policy: str      # "local" | "may-train" | "unverified"
    note: str = ""


PROVIDERS: dict[str, Provider] = {p.name: p for p in [
    Provider("ollama", "http://127.0.0.1:11434/v1", "", "qwen3:14b", "local",
             "Local, confidentiel. Le modèle doit être installé (ollama pull)."),
    Provider("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-120b", "unverified",
             "30 RPM, 1000 RPD"),
    Provider("mistral", "https://api.mistral.ai/v1", "MISTRAL_API_KEY", "mistral-large-latest", "may-train",
             "Mode gratuit : prompts utilisables pour l'entraînement sauf opt-out. Bon en français/arabe."),
    Provider("gemini", "https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY",
             "gemini-2.5-flash", "may-train", "Palier gratuit : prompts utilisables par Google."),
    Provider("openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY",
             "nvidia/nemotron-3-super-120b-a12b:free", "unverified", "20 RPM, 50 RPD sur les modèles :free"),
    Provider("nvidia", "https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY",
             "nvidia/nemotron-3-super-120b-a12b", "unverified", "40 RPM"),
    Provider("huggingface", "https://router.huggingface.co/v1", "HF_TOKEN",
             "meta-llama/Llama-3.1-8B-Instruct", "unverified", "Crédit mensuel très limité"),
    Provider("ovh", "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1", "", "gpt-oss-120b", "unverified",
             "Hébergé dans l'UE, anonyme, 2 RPM par IP"),
]}

RETRYABLE = {408, 429, 500, 502, 503, 504}


class ProviderError(RuntimeError):
    def __init__(self, msg: str, retryable: bool = False):
        super().__init__(msg)
        self.retryable = retryable


def openai_compatible_chat(provider: str | Provider, model: str | None = None, max_tokens: int = 4000,
                           temperature: float = 0.2, timeout: int = 120, allow_remote: bool = False) -> Chat:
    p = PROVIDERS[provider] if isinstance(provider, str) else provider
    if p.data_policy != "local" and not allow_remote:
        raise PermissionError(
            f"« {p.name} » envoie le document à un tiers ({p.data_policy}). Utilisez un document non confidentiel "
            f"et --allow-free-tier, ou le fournisseur local « ollama ».")
    key = os.environ.get(p.env_key, "") if p.env_key else ""
    if p.env_key and not key:
        raise RuntimeError(f"{p.env_key} is not set (clé API {p.name})")
    url = p.base_url.rstrip("/") + "/chat/completions"

    def chat(messages: list[dict], system: str) -> str:
        body = json.dumps({"model": model or p.model, "temperature": temperature, "max_tokens": max_tokens,
                           "messages": [{"role": "system", "content": system}, *messages]}).encode()
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        req = urllib.request.Request(url, body, headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.load(r)
        except urllib.error.HTTPError as e:
            raise ProviderError(f"{p.name}: HTTP {e.code} {e.read()[:200]!r}", e.code in RETRYABLE) from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise ProviderError(f"{p.name}: {e}", True) from e
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, AttributeError) as e:
            raise ProviderError(f"{p.name}: réponse inattendue", True) from e

    return chat


def fallback_chat(chats: list[Chat], retries_per_chat: int = 1, backoff: float = 2.0) -> Chat:
    """Try each provider in order; move on to the next after a retryable failure."""
    def chat(messages: list[dict], system: str) -> str:
        last: Exception | None = None
        for c in chats:
            for attempt in range(retries_per_chat + 1):
                try:
                    return c(messages, system)
                except ProviderError as e:
                    last = e
                    if not e.retryable:
                        break
                    if attempt < retries_per_chat:
                        time.sleep(backoff * (attempt + 1))
        raise RuntimeError(f"Tous les fournisseurs ont échoué : {last}")
    return chat


def build_chat(spec: str, model: str | None = None, allow_remote: bool = False) -> Chat:
    """spec: 'anthropic' or a comma-separated fallback list such as 'ollama,mistral,groq'."""
    from .llm import anthropic_chat
    names = [s.strip() for s in spec.split(",") if s.strip()]
    chats = []
    for n in names:
        if n == "anthropic":
            chats.append(anthropic_chat(model or "claude-sonnet-5-5"))
        elif n in PROVIDERS:
            chats.append(openai_compatible_chat(n, model if len(names) == 1 else None, allow_remote=allow_remote))
        else:
            raise ValueError(f"Fournisseur inconnu : {n}. Disponibles : anthropic, {', '.join(PROVIDERS)}")
    return chats[0] if len(chats) == 1 else fallback_chat(chats)
