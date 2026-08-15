import os

# ---------------------------------------------------------------------------
# Connexion Gemini (LLM cloud gratuit)
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
# Clé obtenue gratuitement sur https://aistudio.google.com/apikey
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_BASE = os.environ.get("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta")
GEMINI_TIMEOUT_SECONDS = int(os.environ.get("GEMINI_TIMEOUT_SECONDS", "60"))
# Délai minimum (secondes) entre deux appels Gemini, pour rester sous le quota gratuit par minute
GEMINI_MIN_INTERVAL_SECONDS = float(os.environ.get("GEMINI_MIN_INTERVAL_SECONDS", "4"))

# ---------------------------------------------------------------------------
# Authentification (l'app est désormais exposée publiquement, plus seulement
# sur le réseau local) — protège le dashboard et l'API par Basic Auth.
# Laisser SENTINEL_PASSWORD vide désactive l'authentification (déconseillé en public).
# ---------------------------------------------------------------------------
SENTINEL_USERNAME = os.environ.get("SENTINEL_USERNAME", "admin")
SENTINEL_PASSWORD = os.environ.get("SENTINEL_PASSWORD", "")

# ---------------------------------------------------------------------------
# Base de données (Postgres, ex. Neon — gratuit, sans carte bancaire, persistant)
# ---------------------------------------------------------------------------
# Format : postgresql://user:password@host/dbname?sslmode=require
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# ---------------------------------------------------------------------------
# Planification
# ---------------------------------------------------------------------------
TIMEZONE = os.environ.get("TIMEZONE", "Europe/Paris")
# Heures des bilans automatiques (format HH:MM séparées par des virgules)
BRIEFING_TIMES = [t.strip() for t in os.environ.get("BRIEFING_TIMES", "07:00,19:00").split(",") if t.strip()]
COLLECT_INTERVAL_MINUTES = int(os.environ.get("COLLECT_INTERVAL_MINUTES", "30"))
CLASSIFY_BATCH_SIZE = int(os.environ.get("CLASSIFY_BATCH_SIZE", "15"))
# Nombre d'heures d'articles à considérer pour un bilan si aucun bilan précédent n'existe
BRIEFING_LOOKBACK_HOURS_DEFAULT = int(os.environ.get("BRIEFING_LOOKBACK_HOURS_DEFAULT", "14"))

# ---------------------------------------------------------------------------
# Thématiques de veille
# ---------------------------------------------------------------------------
THEMES = [
    "Sécurité",
    "Défense",
    "Diplomatie",
    "Économie",
    "Politique intérieure",
    "Ingérences étrangères",
    "Cybersécurité",
    "Renseignement",
    "Terrorisme",
    "Énergie",
    "Migrations",
    "Commerce international",
    "Technologies critiques",
    "Justice internationale",
    "Environnement & ressources",
]

# ---------------------------------------------------------------------------
# Zones géographiques
# ---------------------------------------------------------------------------
ZONES = [
    "Monde",
    "Europe",
    "Eurasie",       # Russie, Asie centrale, Caucase
    "Moyen-Orient",
    "Afrique",
    "Asie",          # Asie du Sud, du Sud-Est, Asie orientale
    "Océanie",
    "Amérique du Nord",
    "Amérique du Sud",
]

# ---------------------------------------------------------------------------
# Mots-clés déclenchant une alerte automatique (haute intensité), indépendamment
# du score de tension donné par le LLM. Insensible à la casse, recherche simple.
# ---------------------------------------------------------------------------
ALERT_KEYWORDS = [
    "invasion", "frappe aérienne", "frappe militaire", "coup d'État", "coup d'Etat",
    "attentat", "prise d'otages", "cyberattaque majeure", "mobilisation générale",
    "ultimatum", "rupture diplomatique", "état d'urgence", "etat d'urgence",
    "arme nucléaire", "essai nucléaire", "assassinat", "putsch", "insurrection",
    "déclaration de guerre", "declaration de guerre", "sanctions massives",
    "expulsion d'ambassadeur", "loi martiale", "embargo",
]

# Seuil au-delà duquel un score de tension (0-100) déclenche une alerte
ALERT_TENSION_THRESHOLD = int(os.environ.get("ALERT_TENSION_THRESHOLD", "80"))
