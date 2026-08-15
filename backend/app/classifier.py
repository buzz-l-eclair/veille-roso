import logging

from . import database as db
from . import llm
from . import config
from .alerts import check_article_for_alerts


logger = logging.getLogger("sentinel.classifier")


SYSTEM_PROMPT = f"""
Tu es un analyste de veille internationale spécialisé en géopolitique,
sécurité et défense.

Tu classes des articles de presse avec rigueur et neutralité,
sans prendre parti.

Tu réponds UNIQUEMENT en JSON valide.
Aucun texte avant ou après le JSON.
"""


THEME_LIST = ", ".join(config.THEMES)
ZONE_LIST = ", ".join(config.ZONES)


def _build_prompt(article: dict) -> str:

    return f"""
Analyse cet article de presse et classe-le.

TITRE:
{article.get("title", "")}

SOURCE:
{article.get("source", "")}

RESUME BRUT:
{(article.get("raw_summary") or "")[:1500]}

Réponds avec EXACTEMENT cet objet JSON :

{{
  "theme": "un thème parmi [{THEME_LIST}]",
  "zone": "une zone parmi [{ZONE_LIST}]",
  "summary_fr": "résumé neutre et factuel en français, 2 à 3 phrases maximum",
  "relevance_score": 0,
  "tension_score": 0
}}

Contraintes :

- theme doit être exactement l'un des thèmes autorisés.
- zone doit être exactement l'une des zones autorisées.
- relevance_score est un entier entre 0 et 100.
- tension_score est un entier entre 0 et 100.
- summary_fr doit être en français.
- Ne mets aucun Markdown.
- Ne mets aucun commentaire.
- Retourne uniquement le JSON.

Si l'article est hors sujet (sport, people, fait divers local sans portée
géopolitique), donne relevance_score inférieur à 20.

Utilise "Monde" uniquement si le sujet est réellement transnational ou global.
"""


def classify_batch(batch_size: int = None) -> dict:

    batch_size = (
        batch_size
        or config.CLASSIFY_BATCH_SIZE
    )

    logger.info(
        "Début classification : récupération de %s articles candidats",
        batch_size,
    )

    articles = db.get_unclassified_articles(
        batch_size
    )

    logger.info(
        "Articles candidats récupérés : %s",
        len(articles),
    )

    processed = 0
    errors = 0
    alerts_raised = 0

    for article in articles:

        article_id = article.get("id")

        title = article.get(
            "title",
            ""
        )

        logger.info(
            "Classification article id=%s : %s",
            article_id,
            title[:120],
        )

        try:

            # -------------------------------------------------
            # Appel Gemini
            # -------------------------------------------------

            result = llm.generate_json(
                _build_prompt(article),
                system=SYSTEM_PROMPT,
            )

            logger.info(
                "Réponse Gemini reçue pour article %s : %s",
                article_id,
                result,
            )

            # -------------------------------------------------
            # Validation thème
            # -------------------------------------------------

            theme = result.get("theme")

            if theme not in config.THEMES:

                logger.warning(
                    "Thème invalide article %s : %r",
                    article_id,
                    theme,
                )

                theme = "Politique intérieure"

            # -------------------------------------------------
            # Validation zone
            # -------------------------------------------------

            zone = result.get("zone")

            if zone not in config.ZONES:

                logger.warning(
                    "Zone invalide article %s : %r",
                    article_id,
                    zone,
                )

                zone = (
                    article.get("zone")
                    or "Monde"
                )

            # -------------------------------------------------
            # Résumé
            # -------------------------------------------------

            summary_fr = str(
                result.get(
                    "summary_fr",
                    ""
                )
            ).strip()

            summary_fr = summary_fr[:600]

            # -------------------------------------------------
            # Scores
            # -------------------------------------------------

            try:

                relevance = int(
                    result.get(
                        "relevance_score",
                        0
                    )
                    or 0
                )

            except (ValueError, TypeError):

                relevance = 0

            try:

                tension = int(
                    result.get(
                        "tension_score",
                        0
                    )
                    or 0
                )

            except (ValueError, TypeError):

                tension = 0

            relevance = max(
                0,
                min(100, relevance)
            )

            tension = max(
                0,
                min(100, tension)
            )

            # -------------------------------------------------
            # Statut
            # -------------------------------------------------

            status = (
                "classified"
                if relevance >= 15
                else "irrelevant"
            )

            logger.info(
                "Article %s -> zone=%s theme=%s "
                "relevance=%s tension=%s status=%s",
                article_id,
                zone,
                theme,
                relevance,
                tension,
                status,
            )

            # -------------------------------------------------
            # Écriture DB
            # -------------------------------------------------

            db.update_article_classification(
                article_id,
                zone,
                theme,
                summary_fr,
                relevance,
                tension,
                status=status,
            )

            logger.info(
                "Article %s enregistré en base.",
                article_id,
            )

            # -------------------------------------------------
            # Alertes
            # -------------------------------------------------

            if status == "classified":

                article_full = dict(article)

                article_full.update(
                    {
                        "zone": zone,
                        "theme": theme,
                        "summary_fr": summary_fr,
                        "relevance_score": relevance,
                        "tension_score": tension,
                    }
                )

                try:

                    if check_article_for_alerts(
                        article_full
                    ):

                        alerts_raised += 1

                except Exception as alert_error:

                    logger.exception(
                        "Erreur alerte article %s : %s",
                        article_id,
                        alert_error,
                    )

            processed += 1

        except llm.OllamaError as e:

            logger.error(
                "ERREUR GEMINI article %s : %s",
                article_id,
                e,
            )

            try:

                db.mark_article_status(
                    article_id,
                    "error"
                )

            except Exception:

                logger.exception(
                    "Impossible de marquer article %s en erreur",
                    article_id,
                )

            errors += 1

        except Exception as e:

            logger.exception(
                "ERREUR INATTENDUE article %s : %s",
                article_id,
                e,
            )

            try:

                db.mark_article_status(
                    article_id,
                    "error"
                )

            except Exception:

                logger.exception(
                    "Impossible de marquer article %s en erreur",
                    article_id,
                )

            errors += 1

    logger.info(
        "FIN CLASSIFICATION : "
        "processed=%s errors=%s alerts=%s remaining=%s",
        processed,
        errors,
        alerts_raised,
        len(articles),
    )

    return {
        "processed": processed,
        "errors": errors,
        "alerts_raised": alerts_raised,
        "remaining_candidates": len(articles),
    }