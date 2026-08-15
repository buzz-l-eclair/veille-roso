import contextlib
import hashlib
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import dict_row

from . import config

# Postgres (Neon) : le schéma est équivalent à la version SQLite, avec une
# recherche plein texte via tsvector/GIN à la place de FTS5.
SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS articles (
        id SERIAL PRIMARY KEY,
        url_hash TEXT UNIQUE NOT NULL,
        url TEXT NOT NULL,
        title TEXT NOT NULL,
        source TEXT NOT NULL,
        raw_summary TEXT,
        published_at TEXT,
        fetched_at TEXT NOT NULL,
        zone TEXT,
        theme TEXT,
        language TEXT,
        summary_fr TEXT,
        relevance_score INTEGER,
        tension_score INTEGER,
        status TEXT NOT NULL DEFAULT 'new',
        search_vector tsvector
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status)",
    "CREATE INDEX IF NOT EXISTS idx_articles_zone ON articles(zone)",
    "CREATE INDEX IF NOT EXISTS idx_articles_theme ON articles(theme)",
    "CREATE INDEX IF NOT EXISTS idx_articles_fetched ON articles(fetched_at)",
    "CREATE INDEX IF NOT EXISTS idx_articles_search ON articles USING GIN(search_vector)",
    """
    CREATE OR REPLACE FUNCTION articles_search_vector_update() RETURNS trigger AS $$
    BEGIN
        NEW.search_vector := to_tsvector('french',
            coalesce(NEW.title, '') || ' ' || coalesce(NEW.summary_fr, '') || ' ' || coalesce(NEW.raw_summary, ''));
        RETURN NEW;
    END
    $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS trg_articles_search_vector ON articles",
    """
    CREATE TRIGGER trg_articles_search_vector
    BEFORE INSERT OR UPDATE ON articles
    FOR EACH ROW EXECUTE FUNCTION articles_search_vector_update()
    """,
    """
    CREATE TABLE IF NOT EXISTS briefings (
        id SERIAL PRIMARY KEY,
        created_at TEXT NOT NULL,
        period TEXT NOT NULL,
        zone TEXT NOT NULL,
        content_md TEXT NOT NULL,
        article_count INTEGER NOT NULL DEFAULT 0
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_briefings_zone ON briefings(zone)",
    "CREATE INDEX IF NOT EXISTS idx_briefings_created ON briefings(created_at)",
    """
    CREATE TABLE IF NOT EXISTS alerts (
        id SERIAL PRIMARY KEY,
        created_at TEXT NOT NULL,
        article_id INTEGER REFERENCES articles(id),
        reason TEXT NOT NULL,
        severity TEXT NOT NULL,
        zone TEXT,
        theme TEXT,
        title TEXT,
        url TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at)",
    """
    CREATE TABLE IF NOT EXISTS feed_runs (
        id SERIAL PRIMARY KEY,
        checked_at TEXT NOT NULL,
        source TEXT NOT NULL,
        status TEXT NOT NULL,
        new_count INTEGER NOT NULL DEFAULT 0,
        detail TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_feed_runs_source ON feed_runs(source)",
    "CREATE INDEX IF NOT EXISTS idx_feed_runs_checked ON feed_runs(checked_at)",
]


def get_conn():
    conn = psycopg.connect(config.DATABASE_URL, row_factory=dict_row, autocommit=False)
    return conn


def init_db():
    with contextlib.closing(get_conn()) as conn:
        with conn.cursor() as cur:
            for stmt in SCHEMA_STATEMENTS:
                cur.execute(stmt)
        conn.commit()


def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def _since_iso(hours: int) -> str:
    return (datetime.utcnow() - timedelta(hours=hours)).isoformat()


# ------------------------------------------------------------------ articles

def article_exists(url: str) -> bool:
    with contextlib.closing(get_conn()) as conn:
        row = conn.execute(
            "SELECT 1 FROM articles WHERE url_hash = %s", (url_hash(url),)
        ).fetchone()
        return row is not None


def insert_article(title, url, source, raw_summary, published_at, zone_hint, theme_hint, language=None):
    with contextlib.closing(get_conn()) as conn:
        try:
            conn.execute(
                """INSERT INTO articles
                   (url_hash, url, title, source, raw_summary, published_at,
                    fetched_at, zone, theme, language, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'new')""",
                (
                    url_hash(url), url, title, source, raw_summary, published_at,
                    now_iso(), zone_hint, theme_hint, language,
                ),
            )
            conn.commit()
            return True
        except psycopg.errors.UniqueViolation:
            conn.rollback()
            return False


def get_unclassified_articles(limit: int):
    with contextlib.closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT * FROM articles WHERE status = 'new' ORDER BY fetched_at ASC LIMIT %s",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_article_classification(article_id, zone, theme, summary_fr, relevance_score, tension_score, status="classified"):
    with contextlib.closing(get_conn()) as conn:
        conn.execute(
            """UPDATE articles SET zone=%s, theme=%s, summary_fr=%s, relevance_score=%s,
               tension_score=%s, status=%s WHERE id=%s""",
            (zone, theme, summary_fr, relevance_score, tension_score, status, article_id),
        )
        conn.commit()


def mark_article_status(article_id, status):
    with contextlib.closing(get_conn()) as conn:
        conn.execute("UPDATE articles SET status=%s WHERE id=%s", (status, article_id))
        conn.commit()


def get_articles(zone=None, theme=None, language=None, hours=48, limit=200, min_relevance=0):
    since = _since_iso(hours)
    query = "SELECT * FROM articles WHERE status='classified' AND fetched_at >= %s"
    params = [since]
    if zone and zone != "Monde":
        query += " AND zone = %s"
        params.append(zone)
    if theme:
        query += " AND theme = %s"
        params.append(theme)
    if language:
        query += " AND language = %s"
        params.append(language)
    if min_relevance:
        query += " AND relevance_score >= %s"
        params.append(min_relevance)
    query += " ORDER BY fetched_at DESC LIMIT %s"
    params.append(limit)
    with contextlib.closing(get_conn()) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_languages():
    with contextlib.closing(get_conn()) as conn:
        rows = conn.execute(
            """SELECT language, COUNT(*) as n FROM articles
               WHERE status='classified' AND language IS NOT NULL
               GROUP BY language ORDER BY n DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


def get_articles_since_last_briefing(zone, fallback_hours):
    with contextlib.closing(get_conn()) as conn:
        last = conn.execute(
            "SELECT created_at FROM briefings WHERE zone=%s ORDER BY created_at DESC LIMIT 1",
            (zone,),
        ).fetchone()
        since = last["created_at"] if last else _since_iso(fallback_hours)
        query = "SELECT * FROM articles WHERE status='classified' AND fetched_at >= %s"
        params = [since]
        if zone != "Monde":
            query += " AND zone = %s"
            params.append(zone)
        query += " ORDER BY tension_score DESC, relevance_score DESC LIMIT 120"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def search_articles(query_text: str, limit: int = 25):
    with contextlib.closing(get_conn()) as conn:
        try:
            rows = conn.execute(
                """SELECT * FROM articles
                   WHERE status = 'classified'
                   AND search_vector @@ websearch_to_tsquery('french', %s)
                   ORDER BY ts_rank(search_vector, websearch_to_tsquery('french', %s)) DESC,
                            fetched_at DESC
                   LIMIT %s""",
                (query_text, query_text, limit),
            ).fetchall()
            if rows:
                return [dict(r) for r in rows]
        except psycopg.Error:
            pass
        # repli simple si la recherche plein texte ne donne rien ou echoue
        with contextlib.closing(get_conn()) as conn2:
            like = f"%{query_text}%"
            rows = conn2.execute(
                """SELECT * FROM articles WHERE status='classified'
                   AND (title ILIKE %s OR summary_fr ILIKE %s)
                   ORDER BY fetched_at DESC LIMIT %s""",
                (like, like, limit),
            ).fetchall()
            return [dict(r) for r in rows]


def get_stats():
    since_48h = _since_iso(48)
    with contextlib.closing(get_conn()) as conn:
        by_zone = conn.execute(
            """SELECT zone, COUNT(*) as n, AVG(tension_score) as avg_tension
               FROM articles WHERE status='classified' AND fetched_at >= %s
               GROUP BY zone""",
            (since_48h,),
        ).fetchall()
        by_theme = conn.execute(
            """SELECT theme, COUNT(*) as n
               FROM articles WHERE status='classified' AND fetched_at >= %s
               GROUP BY theme""",
            (since_48h,),
        ).fetchall()
        total_new = conn.execute("SELECT COUNT(*) as n FROM articles WHERE status='new'").fetchone()["n"]
        return {
            "by_zone": [dict(r) for r in by_zone],
            "by_theme": [dict(r) for r in by_theme],
            "pending_classification": total_new,
        }


# ------------------------------------------------------------------ briefings

def save_briefing(zone, period, content_md, article_count):
    with contextlib.closing(get_conn()) as conn:
        conn.execute(
            "INSERT INTO briefings (created_at, period, zone, content_md, article_count) VALUES (%s, %s, %s, %s, %s)",
            (now_iso(), period, zone, content_md, article_count),
        )
        conn.commit()


def get_latest_briefings(zone=None):
    with contextlib.closing(get_conn()) as conn:
        if zone:
            rows = conn.execute(
                "SELECT * FROM briefings WHERE zone=%s ORDER BY created_at DESC LIMIT 5", (zone,)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT b.* FROM briefings b
                   INNER JOIN (
                       SELECT zone, MAX(created_at) as max_created FROM briefings GROUP BY zone
                   ) latest ON b.zone = latest.zone AND b.created_at = latest.max_created
                   ORDER BY CASE WHEN b.zone='Monde' THEN 0 ELSE 1 END, b.zone"""
            ).fetchall()
        return [dict(r) for r in rows]


def get_briefings_history(zone=None, limit=30):
    with contextlib.closing(get_conn()) as conn:
        if zone:
            rows = conn.execute(
                "SELECT * FROM briefings WHERE zone=%s ORDER BY created_at DESC LIMIT %s", (zone, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM briefings ORDER BY created_at DESC LIMIT %s", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


# ------------------------------------------------------------------ alerts

def insert_alert(article_id, reason, severity, zone, theme, title, url):
    with contextlib.closing(get_conn()) as conn:
        conn.execute(
            """INSERT INTO alerts (created_at, article_id, reason, severity, zone, theme, title, url)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (now_iso(), article_id, reason, severity, zone, theme, title, url),
        )
        conn.commit()


def get_recent_alerts(limit=50):
    with contextlib.closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT * FROM alerts ORDER BY created_at DESC LIMIT %s", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ------------------------------------------------------------------ feed health

def record_feed_run(source: str, status: str, new_count: int = 0, detail: str = None):
    with contextlib.closing(get_conn()) as conn:
        conn.execute(
            """INSERT INTO feed_runs (checked_at, source, status, new_count, detail)
               VALUES (%s, %s, %s, %s, %s)""",
            (now_iso(), source, status, new_count, detail),
        )
        conn.commit()


def get_feed_status():
    """Renvoie le dernier statut connu de chaque flux (le plus récent en premier)."""
    with contextlib.closing(get_conn()) as conn:
        rows = conn.execute(
            """SELECT DISTINCT ON (source) source, checked_at, status, new_count, detail
               FROM feed_runs
               ORDER BY source, checked_at DESC"""
        ).fetchall()
        rows = [dict(r) for r in rows]
        rows.sort(key=lambda r: r["checked_at"], reverse=True)
        return rows


# ------------------------------------------------------------------ analytics / timeline

def get_daily_stats(days: int = 14):
    """Volume d'articles et tension moyenne par jour (toutes zones), pour les graphiques."""
    since = _since_iso(days * 24)
    with contextlib.closing(get_conn()) as conn:
        rows = conn.execute(
            """SELECT substring(fetched_at from 1 for 10) as day,
                      COUNT(*) as n,
                      AVG(tension_score) as avg_tension,
                      MAX(tension_score) as max_tension
               FROM articles
               WHERE status='classified' AND fetched_at >= %s
               GROUP BY day
               ORDER BY day ASC""",
            (since,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_daily_stats_by_zone(days: int = 14):
    """Idem mais ventilé par zone, pour comparer les zones dans le temps."""
    since = _since_iso(days * 24)
    with contextlib.closing(get_conn()) as conn:
        rows = conn.execute(
            """SELECT substring(fetched_at from 1 for 10) as day, zone,
                      COUNT(*) as n,
                      AVG(tension_score) as avg_tension
               FROM articles
               WHERE status='classified' AND fetched_at >= %s
               GROUP BY day, zone
               ORDER BY day ASC""",
            (since,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_theme_distribution(hours: int = 168):
    since = _since_iso(hours)
    with contextlib.closing(get_conn()) as conn:
        rows = conn.execute(
            """SELECT theme, COUNT(*) as n, AVG(tension_score) as avg_tension
               FROM articles
               WHERE status='classified' AND fetched_at >= %s
               GROUP BY theme
               ORDER BY n DESC""",
            (since,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_source_distribution(hours: int = 168, limit: int = 20):
    since = _since_iso(hours)
    with contextlib.closing(get_conn()) as conn:
        rows = conn.execute(
            """SELECT source, COUNT(*) as n, AVG(tension_score) as avg_tension
               FROM articles
               WHERE status='classified' AND fetched_at >= %s
               GROUP BY source
               ORDER BY n DESC
               LIMIT %s""",
            (since, limit),
        ).fetchall()
        return [dict(r) for r in rows]
