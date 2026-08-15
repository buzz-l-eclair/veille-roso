import logging
from datetime import datetime

import feedparser

from . import database as db
from .feeds import FEEDS

logger = logging.getLogger("sentinel.collector")


def _parse_date(entry) -> str:
    for key in ("published_parsed", "updated_parsed"):
        val = getattr(entry, key, None)
        if val:
            try:
                return datetime(*val[:6]).isoformat()
            except (TypeError, ValueError):
                continue
    return db.now_iso()


def collect_all() -> dict:
    """Parcourt tous les flux configures et insere les nouveaux articles.
    Renvoie un resume {flux: nb_nouveaux_articles}."""
    summary = {}
    total_new = 0
    for name, url, zone_hint, theme_hint in FEEDS:
        try:
            parsed = feedparser.parse(url)
        except Exception as e:  # feedparser est tolerant, mais on securise
            logger.warning("Echec parsing flux %s (%s): %s", name, url, e)
            summary[name] = "erreur"
            continue

        if getattr(parsed, "bozo", 0) and not parsed.entries:
            summary[name] = "erreur (flux illisible)"
            continue

        new_count = 0
        for entry in parsed.entries[:40]:
            link = entry.get("link")
            title = entry.get("title")
            if not link or not title:
                continue
            if db.article_exists(link):
                continue
            raw_summary = entry.get("summary", "") or entry.get("description", "")
            published_at = _parse_date(entry)
            inserted = db.insert_article(
                title=title.strip(),
                url=link.strip(),
                source=name,
                raw_summary=raw_summary[:2000] if raw_summary else "",
                published_at=published_at,
                zone_hint=zone_hint,
                theme_hint=theme_hint,
            )
            if inserted:
                new_count += 1
        summary[name] = new_count
        total_new += new_count

    logger.info("Collecte terminee : %d nouveaux articles au total", total_new)
    summary["_total_new"] = total_new
    return summary
