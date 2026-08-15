import json
import re
import threading
import time
import httpx

from . import config

_last_call_lock = threading.Lock()
_last_call_ts = 0.0


def _throttle():
    """Espace les appels Gemini pour limiter les erreurs de quota."""
    global _last_call_ts

    with _last_call_lock:
        wait = config.GEMINI_MIN_INTERVAL_SECONDS - (
            time.monotonic() - _last_call_ts
        )

        if wait > 0:
            time.sleep(wait)

        _last_call_ts = time.monotonic()


class OllamaError(Exception):
    """
    Ancien nom conservé pour compatibilité avec le reste du projet.
    Les erreurs concernent désormais Gemini.
    """
    pass


def _extract_json(text: str):
    """Extrait un objet JSON valide depuis la réponse Gemini."""

    if not text:
        return None

    text = text.strip()

    # Retire les fences Markdown
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    text = text.strip()

    # Tentative directe
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Recherche d'un objet JSON dans la réponse
    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def _endpoint(model: str) -> str:
    return f"{config.GEMINI_API_BASE}/models/{model}:generateContent"


def generate(
    prompt: str,
    system: str = "",
    json_mode: bool = False,
    temperature: float = 0.2,
) -> str:

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": temperature,
        },
    }

    if system:
        payload["systemInstruction"] = {
            "parts": [
                {
                    "text": system
                }
            ]
        }

    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    if not config.GEMINI_API_KEY:
        raise OllamaError(
            "GEMINI_API_KEY n'est pas configurée."
        )

    logger_msg = (
        f"Gemini request model={config.GEMINI_MODEL} "
        f"json_mode={json_mode}"
    )

    print(f"[LLM] {logger_msg}", flush=True)

    _throttle()

    try:
        resp = httpx.post(
            _endpoint(config.GEMINI_MODEL),
            params={
                "key": config.GEMINI_API_KEY
            },
            json=payload,
            timeout=config.GEMINI_TIMEOUT_SECONDS,
        )

        print(
            f"[LLM] Gemini HTTP {resp.status_code}",
            flush=True
        )

        resp.raise_for_status()

        data = resp.json()

    except httpx.HTTPStatusError as e:

        status = e.response.status_code

        print(
            f"[LLM ERROR] HTTP {status}: "
            f"{e.response.text[:1000]}",
            flush=True,
        )

        if status == 429:
            raise OllamaError(
                "Quota Gemini dépassé (429)."
            )

        if status == 400:
            raise OllamaError(
                f"Requête Gemini invalide (400): "
                f"{e.response.text[:1000]}"
            )

        if status == 401 or status == 403:
            raise OllamaError(
                f"Clé API Gemini refusée ({status}): "
                f"{e.response.text[:1000]}"
            )

        raise OllamaError(
            f"Erreur API Gemini ({status}): "
            f"{e.response.text[:1000]}"
        )

    except httpx.HTTPError as e:

        print(
            f"[LLM ERROR] Connexion Gemini: {e}",
            flush=True,
        )

        raise OllamaError(
            f"Erreur de connexion à Gemini: {e}"
        )

    # ---------------------------------------------------------
    # Analyse de la réponse Gemini
    # ---------------------------------------------------------

    try:

        candidates = data.get("candidates") or []

        if not candidates:

            block_reason = (
                data.get("promptFeedback") or {}
            ).get("blockReason")

            print(
                f"[LLM ERROR] Aucun candidat Gemini. "
                f"blockReason={block_reason}. "
                f"response={str(data)[:1000]}",
                flush=True,
            )

            if block_reason:
                raise OllamaError(
                    f"Réponse bloquée par Gemini: {block_reason}"
                )

            raise OllamaError(
                f"Gemini n'a retourné aucun candidat: "
                f"{str(data)[:1000]}"
            )

        candidate = candidates[0]

        finish_reason = candidate.get(
            "finishReason"
        )

        print(
            f"[LLM] finishReason={finish_reason}",
            flush=True,
        )

        content = candidate.get("content") or {}

        parts = content.get("parts") or []

        texts = []

        for part in parts:

            text = part.get("text")

            if text:
                texts.append(text)

        result = "".join(texts).strip()

        print(
            f"[LLM] Réponse reçue ({len(result)} caractères)",
            flush=True,
        )

        if not result:

            print(
                f"[LLM ERROR] Réponse vide Gemini: "
                f"{str(data)[:1000]}",
                flush=True,
            )

            raise OllamaError(
                "Gemini a retourné une réponse vide."
            )

        return result

    except OllamaError:
        raise

    except Exception as e:

        print(
            f"[LLM ERROR] Réponse Gemini inattendue: "
            f"{e} — {str(data)[:1000]}",
            flush=True,
        )

        raise OllamaError(
            f"Réponse Gemini inattendue: {e}"
        )


def generate_json(
    prompt: str,
    system: str = "",
    temperature: float = 0.1,
):

    raw = generate(
        prompt,
        system=system,
        json_mode=True,
        temperature=temperature,
    )

    parsed = _extract_json(raw)

    if parsed is None:

        print(
            "[LLM ERROR] JSON Gemini inexploitable:",
            flush=True,
        )

        print(
            raw[:2000],
            flush=True,
        )

        raise OllamaError(
            f"Réponse LLM non-JSON exploitable: "
            f"{raw[:500]}"
        )

    if not isinstance(parsed, dict):

        print(
            f"[LLM ERROR] JSON reçu mais pas un objet: "
            f"{type(parsed)}",
            flush=True,
        )

        raise OllamaError(
            "Gemini a retourné un JSON qui n'est pas un objet."
        )

    print(
        f"[LLM] JSON valide reçu: "
        f"{list(parsed.keys())}",
        flush=True,
    )

    return parsed


def check_connection() -> bool:

    if not config.GEMINI_API_KEY:
        return False

    try:

        resp = httpx.get(
            f"{config.GEMINI_API_BASE}/models/{config.GEMINI_MODEL}",
            params={
                "key": config.GEMINI_API_KEY
            },
            timeout=5,
        )

        return resp.status_code == 200

    except httpx.HTTPError:

        return False