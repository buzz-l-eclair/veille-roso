import json
import re
import threading
import time
import httpx

from . import config

_last_call_lock = threading.Lock()
_last_call_ts = 0.0


def _throttle():
    """Espace les appels pour rester sous le quota gratuit Gemini (limite par minute).
    Réglable via GEMINI_MIN_INTERVAL_SECONDS (défaut 4s ≈ 15 requêtes/minute max)."""
    global _last_call_ts
    with _last_call_lock:
        wait = config.GEMINI_MIN_INTERVAL_SECONDS - (time.monotonic() - _last_call_ts)
        if wait > 0:
            time.sleep(wait)
        _last_call_ts = time.monotonic()


class OllamaError(Exception):
    """Conservé sous ce nom pour compatibilité avec classifier.py / synthesizer.py / rag.py,
    mais couvre maintenant les erreurs de l'API Gemini."""
    pass


def _extract_json(text: str):
    """Extrait le premier objet JSON valide d'une reponse LLM, meme si le
    modele a ajoute du texte ou des ```fences``` autour."""
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _endpoint(model: str) -> str:
    return f"{config.GEMINI_API_BASE}/models/{model}:generateContent"


def generate(prompt: str, system: str = "", json_mode: bool = False, temperature: float = 0.2) -> str:
    """Appelle l'API Gemini (generateContent) et renvoie le texte brut de la reponse."""
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    if not config.GEMINI_API_KEY:
        raise OllamaError(
            "GEMINI_API_KEY n'est pas configurée. Ajoute ta clé API Gemini (obtenue sur "
            "https://aistudio.google.com/apikey) dans les variables d'environnement."
        )

    _throttle()
    try:
        resp = httpx.post(
            _endpoint(config.GEMINI_MODEL),
            params={"key": config.GEMINI_API_KEY},
            json=payload,
            timeout=config.GEMINI_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as e:
        # 429 = quota gratuit journalier/minute dépassé : message clair plutôt qu'une trace brute
        if e.response.status_code == 429:
            raise OllamaError(
                "Quota gratuit Gemini dépassé pour l'instant (limite par minute ou par jour). "
                "Réessaie plus tard ou espace les traitements."
            )
        raise OllamaError(f"Erreur API Gemini ({e.response.status_code}): {e.response.text[:300]}")
    except httpx.HTTPError as e:
        raise OllamaError(f"Erreur de connexion à l'API Gemini: {e}")

    try:
        candidates = data.get("candidates") or []
        if not candidates:
            block_reason = (data.get("promptFeedback") or {}).get("blockReason")
            if block_reason:
                raise OllamaError(f"Réponse bloquée par Gemini (raison: {block_reason})")
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError, TypeError) as e:
        raise OllamaError(f"Réponse Gemini inattendue: {e} — {str(data)[:300]}")


def generate_json(prompt: str, system: str = "", temperature: float = 0.1):
    raw = generate(prompt, system=system, json_mode=True, temperature=temperature)
    parsed = _extract_json(raw)
    if parsed is None:
        raise OllamaError(f"Reponse LLM non-JSON exploitable: {raw[:300]}")
    return parsed


def check_connection() -> bool:
    if not config.GEMINI_API_KEY:
        return False
    try:
        resp = httpx.get(
            f"{config.GEMINI_API_BASE}/models/{config.GEMINI_MODEL}",
            params={"key": config.GEMINI_API_KEY},
            timeout=5,
        )
        return resp.status_code == 200
    except httpx.HTTPError:
        return False
