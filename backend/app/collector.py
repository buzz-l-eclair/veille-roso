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
    """
    Parcourt tous les flux configurés et insère les nouveaux articles.

    Format d'un flux :
    (nom, url, zone_par_defaut, theme_par_defaut, langue)

    La langue est conservée dans FEEDS comme métadonnée mais n'est
    actuellement pas nécessaire à l'insertion en base.
    """

    summary = {}
    total_new = 0

    logger.info("Début de la collecte de %d flux RSS/Atom", len(FEEDS))

    for feed in FEEDS:

        # Accepte le format actuel à 5 champs.
        # Le dernier champ correspond à la langue.
        try:
            name, url, zone_hint, theme_hint, language = feed
        except ValueError:
            logger.error(
                "Flux mal configuré : %r — format attendu "
                "(nom, url, zone, theme, langue)",
                feed,
            )
            continue

        try:
            parsed = feedparser.parse(url)
        except Exception as e:
            logger.warning(
                "Échec parsing flux %s (%s): %s",
                name,
                url,
                e,
            )
            summary[name] = "erreur"
            continue

        # Flux complètement illisible
        if getattr(parsed, "bozo", 0) and not parsed.entries:
            logger.warning(
                "Flux illisible ou vide : %s (%s)",
                name,
                url,
            )
            summary[name] = "erreur (flux illisible)"
            continue

        entries = parsed.entries[:40]
        new_count = 0

        logger.info(
            "Flux %-45s : %d entrées détectées",
            name,
            len(entries),
        )

        for entry in entries:

            link = entry.get("link")
            title = entry.get("title")

            if not link or not title:
                continue

            if db.article_exists(link):
                continue

            raw_summary = (
                entry.get("summary", "")
                or entry.get("description", "")
            )

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

        logger.info(
            "Flux %-45s : %d nouveaux articles",
            name,
            new_count,
        )

    logger.info(
        "Collecte terminée : %d nouveaux articles au total",
        total_new,
    )

    summary["_total_new"] = total_new

    return summary