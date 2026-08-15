import logging

from . import database as db
from . import config

logger = logging.getLogger("sentinel.alerts")


def check_article_for_alerts(article: dict) -> bool:
    """Verifie un article deja classifie et cree une alerte si necessaire.
    Renvoie True si une alerte a ete levee."""
    text = f"{article.get('title', '')} {article.get('summary_fr', '')} {article.get('raw_summary', '')}".lower()

    matched_keyword = None
    for kw in config.ALERT_KEYWORDS:
        if kw.lower() in text:
            matched_keyword = kw
            break

    tension = article.get("tension_score") or 0
    raised = False

    if matched_keyword:
        db.insert_alert(
            article_id=article["id"],
            reason=f"Mot-clé sensible détecté : « {matched_keyword} »",
            severity="keyword",
            zone=article.get("zone"),
            theme=article.get("theme"),
            title=article.get("title"),
            url=article.get("url"),
        )
        raised = True

    if tension >= config.ALERT_TENSION_THRESHOLD:
        db.insert_alert(
            article_id=article["id"],
            reason=f"Score de tension élevé ({tension}/100) évalué par le LLM",
            severity="tension",
            zone=article.get("zone"),
            theme=article.get("theme"),
            title=article.get("title"),
            url=article.get("url"),
        )
        raised = True

    return raised
