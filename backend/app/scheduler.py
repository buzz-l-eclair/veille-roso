import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from . import config
from . import collector
from . import classifier
from . import synthesizer

logger = logging.getLogger("sentinel.scheduler")

_scheduler = BackgroundScheduler(timezone=config.TIMEZONE)


def collect_and_classify_job():
    logger.info("Job collecte+classification demarre")
    try:
        collect_summary = collector.collect_all()
        logger.info("Collecte: %s nouveaux articles", collect_summary.get("_total_new", 0))
    except Exception:
        logger.exception("Erreur pendant la collecte")

    # classifie par lots successifs tant qu'il reste des articles 'new'
    try:
        total_processed = 0
        for _ in range(20):  # garde-fou anti boucle infinie
            result = classifier.classify_batch()
            total_processed += result["processed"]
            if result["processed"] == 0:
                break
        logger.info("Classification: %d articles traites", total_processed)
    except Exception:
        logger.exception("Erreur pendant la classification")


def briefing_job(period_label: str):
    logger.info("Job bilan '%s' demarre", period_label)
    try:
        synthesizer.generate_all_briefings(period_label)
    except Exception:
        logger.exception("Erreur pendant la generation des bilans")


def start_scheduler():
    _scheduler.add_job(
        collect_and_classify_job,
        trigger="interval",
        minutes=config.COLLECT_INTERVAL_MINUTES,
        id="collect_classify",
        next_run_time=None,  # premier run declenche manuellement au demarrage (voir main.py)
        replace_existing=True,
    )

    for t in config.BRIEFING_TIMES:
        hour, minute = t.split(":")
        label = "matin" if int(hour) < 14 else "soir"
        _scheduler.add_job(
            briefing_job,
            trigger=CronTrigger(hour=int(hour), minute=int(minute)),
            args=[label],
            id=f"briefing_{t}",
            replace_existing=True,
        )

    _scheduler.start()
    logger.info("Planificateur demarre : collecte toutes les %d min, bilans a %s",
                config.COLLECT_INTERVAL_MINUTES, ", ".join(config.BRIEFING_TIMES))


def shutdown_scheduler():
    _scheduler.shutdown(wait=False)
