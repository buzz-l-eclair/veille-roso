import logging

from . import database as db
from . import llm
from . import config
from .alerts import check_article_for_alerts

logger = logging.getLogger("sentinel.classifier")

SYSTEM_PROMPT = f"""Tu es un analyste de veille internationale specialise en geopolitique,
securite et defense. Tu classes des depeches de presse avec rigueur et neutralite,
sans prendre parti. Tu reponds UNIQUEMENT en JSON valide, sans aucun texte autour."""

THEME_LIST = ", ".join(config.THEMES)
ZONE_LIST = ", ".join(config.ZONES)


def _build_prompt(article: dict) -> str:
    return f"""Analyse cet article de presse et classe-le.

TITRE: {article['title']}
SOURCE: {article['source']}
RESUME BRUT: {(article.get('raw_summary') or '')[:800]}

Reponds avec un objet JSON strictement de cette forme :
{{
  "theme": "un theme parmi [{THEME_LIST}]",
  "zone": "une zone parmi [{ZONE_LIST}]",
  "summary_fr": "resume neutre et factuel en francais, 2 a 3 phrases maximum",
  "relevance_score": entier de 0 a 100 (pertinence pour une veille securite/defense/diplomatie/economie/politique/ingerence, 0 = hors sujet, 100 = tres pertinent),
  "tension_score": entier de 0 a 100 (niveau de tension ou de gravite geopolitique evoque par l'article, 0 = anodin, 100 = crise majeure)
}}

Si l'article est hors-sujet (sport, people, fait divers local sans portee geopolitique),
mets relevance_score a une valeur basse (inferieur a 20).
Choisis "zone" = "Monde" uniquement si le sujet est vraiment transnational/global.
Reponds uniquement avec le JSON, rien d'autre."""


def classify_batch(batch_size: int = None) -> dict:
    batch_size = batch_size or config.CLASSIFY_BATCH_SIZE
    articles = db.get_unclassified_articles(batch_size)
    processed, errors, alerts_raised = 0, 0, 0

    for article in articles:
        try:
            result = llm.generate_json(_build_prompt(article), system=SYSTEM_PROMPT)
            theme = result.get("theme") if result.get("theme") in config.THEMES else "Politique intérieure"
            zone = result.get("zone") if result.get("zone") in config.ZONES else (article.get("zone") or "Monde")
            summary_fr = str(result.get("summary_fr", ""))[:600]
            relevance = int(result.get("relevance_score", 0) or 0)
            tension = int(result.get("tension_score", 0) or 0)

            status = "classified" if relevance >= 15 else "irrelevant"
            db.update_article_classification(
                article["id"], zone, theme, summary_fr, relevance, tension, status=status
            )

            if status == "classified":
                article_full = dict(article)
                article_full.update({
                    "zone": zone, "theme": theme, "summary_fr": summary_fr,
                    "relevance_score": relevance, "tension_score": tension,
                })
                if check_article_for_alerts(article_full):
                    alerts_raised += 1

            processed += 1
        except llm.OllamaError as e:
            logger.error("Erreur classification article %s: %s", article.get("id"), e)
            db.mark_article_status(article["id"], "error")
            errors += 1
        except Exception as e:
            logger.exception("Erreur inattendue classification article %s: %s", article.get("id"), e)
            db.mark_article_status(article["id"], "error")
            errors += 1

    return {"processed": processed, "errors": errors, "alerts_raised": alerts_raised, "remaining_candidates": len(articles)}
