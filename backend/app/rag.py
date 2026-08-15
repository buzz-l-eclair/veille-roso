import logging

from . import database as db
from . import llm

logger = logging.getLogger("sentinel.rag")

SYSTEM_PROMPT = """Tu es un analyste de veille internationale. Tu reponds a des questions
UNIQUEMENT a partir des depeches fournies en contexte. Si le contexte ne permet pas de
repondre, dis-le explicitement plutot que d'inventer. Cite les sources pertinentes entre
parentheses (nom de la source). Reponds en francais, de maniere factuelle et concise."""


def _format_context(articles: list) -> str:
    lines = []
    for a in articles:
        lines.append(
            f"- ({a.get('source')}, {a.get('published_at', '')[:10]}, zone: {a.get('zone')}, "
            f"theme: {a.get('theme')}) {a.get('title')} — "
            f"{a.get('summary_fr') or (a.get('raw_summary') or '')[:250]}"
        )
    return "\n".join(lines)


def ask(question: str, zone: str = None, theme: str = None, hours: int = 168) -> dict:
    # 1. recherche plein texte sur la question
    candidates = db.search_articles(question, limit=40)

    # 2. complement par filtre zone/theme recent si peu de resultats
    if len(candidates) < 8:
        candidates += db.get_articles(zone=zone, theme=theme, hours=hours, limit=40)

    # dedoublonnage par id en conservant l'ordre
    seen = set()
    unique_articles = []
    for a in candidates:
        if a["id"] not in seen:
            seen.add(a["id"])
            unique_articles.append(a)
    unique_articles = unique_articles[:35]

    if not unique_articles:
        return {
            "answer": "Aucun article pertinent n'a été trouvé dans la base de veille pour répondre à cette question. "
                      "Essaie de reformuler, ou attends la prochaine collecte des flux.",
            "sources": [],
        }

    context = _format_context(unique_articles)
    prompt = f"""CONTEXTE (depeches recentes de la base de veille) :
{context}

QUESTION : {question}

Reponds en t'appuyant exclusivement sur le contexte ci-dessus."""

    try:
        answer = llm.generate(prompt, system=SYSTEM_PROMPT, temperature=0.2)
    except llm.OllamaError as e:
        logger.error("Erreur RAG: %s", e)
        answer = f"Erreur lors de l'appel au LLM local : {e}"

    sources = [
        {"title": a["title"], "url": a["url"], "source": a["source"], "published_at": a.get("published_at")}
        for a in unique_articles[:12]
    ]
    return {"answer": answer, "sources": sources}
