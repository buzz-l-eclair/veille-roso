import logging
import secrets
import threading

from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import config
from . import database as db
from . import collector
from . import classifier
from . import synthesizer
from . import rag
from . import llm
from . import scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sentinel.main")

app = FastAPI(title="Sentinel Géoveille", version="1.0")

# ---------------------------------------------------------------- auth
# L'app est exposée publiquement une fois déployée en ligne : toutes les
# routes sont protégées par Basic Auth si SENTINEL_PASSWORD est défini.
_security = HTTPBasic(auto_error=False)


def require_auth(credentials: HTTPBasicCredentials = Depends(_security)):
    if not config.SENTINEL_PASSWORD:
        return  # auth désactivée (déconseillé en déploiement public)
    valid = credentials is not None and secrets.compare_digest(
        credentials.username, config.SENTINEL_USERNAME
    ) and secrets.compare_digest(credentials.password, config.SENTINEL_PASSWORD)
    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Authentification requise",
            headers={"WWW-Authenticate": "Basic"},
        )


app.router.dependencies.append(Depends(require_auth))


@app.on_event("startup")
def on_startup():
    if not config.DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL n'est pas configurée. Renseigne l'URL de connexion Postgres "
            "(ex. Neon) dans les variables d'environnement."
        )
    db.init_db()
    scheduler.start_scheduler()
    # premiere collecte en arriere-plan pour ne pas bloquer le demarrage
    threading.Thread(target=scheduler.collect_and_classify_job, daemon=True).start()


@app.on_event("shutdown")
def on_shutdown():
    scheduler.shutdown_scheduler()


# ---------------------------------------------------------------- schemas

class AskRequest(BaseModel):
    question: str
    zone: str | None = None
    theme: str | None = None
    hours: int = 168


# ---------------------------------------------------------------- meta

@app.get("/api/health")
def health():
    db_ok = True
    try:
        db.get_stats()
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database_connected": db_ok,
        "llm_configured": bool(config.GEMINI_API_KEY),
    }


@app.get("/api/zones")
def zones():
    return config.ZONES


@app.get("/api/themes")
def themes():
    return config.THEMES


@app.get("/api/feeds")
def feeds():
    from .feeds import FEEDS
    return [
        {"name": n, "url": u, "zone": z, "theme": t, "language": lang}
        for n, u, z, t, lang in FEEDS
    ]


@app.get("/api/feeds/status")
def feeds_status():
    """Dernier statut connu de chaque flux (ok / erreur), pour repérer les flux cassés."""
    from .feeds import FEEDS
    known = {n: {"name": n, "zone": z, "theme": t} for n, u, z, t, lang in FEEDS}
    runs = {r["source"]: r for r in db.get_feed_status()}
    result = []
    for name, meta in known.items():
        run = runs.get(name)
        result.append({
            **meta,
            "status": run["status"] if run else "jamais collecté",
            "last_checked": run["checked_at"] if run else None,
            "new_count": run["new_count"] if run else 0,
            "detail": run["detail"] if run else None,
        })
    result.sort(key=lambda r: (r["status"] != "erreur", r["name"]))
    return result


@app.get("/api/stats")
def stats():
    return db.get_stats()


@app.get("/api/stats/timeline")
def stats_timeline(days: int = 14, by_zone: bool = False):
    if by_zone:
        return db.get_daily_stats_by_zone(days=days)
    return db.get_daily_stats(days=days)


@app.get("/api/stats/themes")
def stats_themes(hours: int = 168):
    return db.get_theme_distribution(hours=hours)


@app.get("/api/stats/sources")
def stats_sources(hours: int = 168, limit: int = 20):
    return db.get_source_distribution(hours=hours, limit=limit)


# ---------------------------------------------------------------- articles

@app.get("/api/articles")
def articles(zone: str = None, theme: str = None, hours: int = 48, limit: int = 200, min_relevance: int = 0):
    return db.get_articles(zone=zone, theme=theme, hours=hours, limit=limit, min_relevance=min_relevance)


@app.get("/api/search")
def search(q: str, limit: int = 25):
    if not q or len(q.strip()) < 2:
        raise HTTPException(400, "Requête de recherche trop courte")
    return db.search_articles(q.strip(), limit=limit)


# ---------------------------------------------------------------- briefings

@app.get("/api/briefings/latest")
def latest_briefings():
    return db.get_latest_briefings()


@app.get("/api/briefings/history")
def briefings_history(zone: str = None, limit: int = 30):
    return db.get_briefings_history(zone=zone, limit=limit)


@app.post("/api/briefings/generate")
def trigger_briefing(zone: str = "Monde"):
    if zone not in config.ZONES:
        raise HTTPException(400, f"Zone inconnue: {zone}")
    return synthesizer.generate_briefing(zone, period_label="manuel")


@app.post("/api/briefings/generate-all")
def trigger_all_briefings(background_tasks: BackgroundTasks):
    background_tasks.add_task(synthesizer.generate_all_briefings, "manuel")
    return {"status": "lancé en arrière-plan"}


# ---------------------------------------------------------------- alerts

@app.get("/api/alerts")
def alerts(limit: int = 50):
    return db.get_recent_alerts(limit=limit)


# ---------------------------------------------------------------- pipeline manuel

@app.post("/api/collect")
def trigger_collect(background_tasks: BackgroundTasks):
    background_tasks.add_task(scheduler.collect_and_classify_job)
    return {"status": "collecte + classification lancées en arrière-plan"}


@app.post("/api/classify")
def trigger_classify():
    return classifier.classify_batch()


# ---------------------------------------------------------------- RAG / question libre

@app.post("/api/ask")
def ask(req: AskRequest):
    if not req.question or len(req.question.strip()) < 3:
        raise HTTPException(400, "Question trop courte")
    return rag.ask(req.question.strip(), zone=req.zone, theme=req.theme, hours=req.hours)


# ---------------------------------------------------------------- frontend statique

app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
def index():
    return FileResponse("frontend/index.html")
