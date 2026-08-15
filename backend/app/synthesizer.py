import logging
from datetime import datetime

from . import database as db
from . import llm
from . import config

logger = logging.getLogger("sentinel.synthesizer")

SYSTEM_PROMPT = """Tu es un analyste senior charge de rediger des bilans de veille
internationale a destination d'un decideur. Style sobre, factuel, structure,
sans sensationnalisme. Tu ne prends pas parti et tu distingues clairement les faits
rapportes des evaluations. Tu rediges en francais."""


def _format_articles_for_prompt(articles: list) -> str:
    lines = []
    for a in articles[:60]:
        lines.append(
            f"- [{a.get('theme')}] {a.get('title')} "
            f"(source: {a.get('source')}, tension: {a.get('tension_score')}/100) "
            f"— {a.get('summary_fr') or a.get('raw_summary', '')[:200]}"
        )
    return "\n".join(lines)


def _build_prompt(zone: str, period_label: str, articles: list) -> str:
    articles_text = _format_articles_for_prompt(articles)
    zone_label = "mondiale (toutes zones confondues)" if zone == "Monde" else f"pour la zone {zone}"
    return f"""Redige le bilan de veille {period_label} {zone_label}, a partir des depeches
suivantes (les plus tendues en premier) :

{articles_text}

Structure attendue en Markdown :
## Synthèse générale
(3 à 5 phrases maximum résumant la situation)

## Points saillants
(liste à puces des développements les plus significatifs, groupés par thématique si pertinent :
Sécurité, Défense, Diplomatie, Économie, Politique, Ingérences étrangères, Cyber, etc.
Ne garde que ce qui est réellement significatif, ignore le bruit.)

## Évaluation du niveau de tension
(une phrase qualifiant le niveau de tension global : faible / modéré / élevé / critique,
avec une brève justification)

## À surveiller
(1 à 3 points qui pourraient évoluer dans les prochaines heures/jours)

Reste concis, factuel, et ne mentionne que ce qui ressort effectivement des depeches
fournies. N'invente aucun fait."""


def generate_briefing(zone: str, period_label: str = "manuel") -> dict:
    articles = db.get_articles_since_last_briefing(zone, config.BRIEFING_LOOKBACK_HOURS_DEFAULT)

    if not articles:
        content = ("## Synthèse générale\nAucun développement notable détecté depuis le dernier bilan "
                   f"pour la zone « {zone} ».\n")
        db.save_briefing(zone, period_label, content, 0)
        return {"zone": zone, "article_count": 0, "content_md": content}

    prompt = _build_prompt(zone, period_label, articles)
    try:
        content = llm.generate(prompt, system=SYSTEM_PROMPT, temperature=0.3)
    except llm.OllamaError as e:
        logger.error("Erreur generation bilan zone=%s: %s", zone, e)
        content = f"## Erreur\nLe LLM local n'a pas pu générer ce bilan : {e}"

    db.save_briefing(zone, period_label, content, len(articles))
    return {"zone": zone, "article_count": len(articles), "content_md": content}


def generate_all_briefings(period_label: str) -> list:
    results = []
    for zone in config.ZONES:
        try:
            results.append(generate_briefing(zone, period_label))
        except Exception as e:
            logger.exception("Erreur bilan zone=%s: %s", zone, e)
    return results
