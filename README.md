# Sentinel — Géoveille internationale

Outil de veille internationale : collecte de flux RSS/Atom, classification et synthèse par
LLM (API Gemini gratuite), bilans automatiques deux fois par jour, alertes, et
interrogation libre de la base de veille. Base de données SQLite locale, aucun service
payant.

Thématiques suivies : Sécurité, Défense, Diplomatie, Économie, Politique intérieure,
Ingérences étrangères, Cybersécurité, Renseignement, Terrorisme, Énergie, Migrations,
Commerce international, Technologies critiques, Justice internationale, Environnement &
ressources.

Zones : Monde, Europe, Eurasie, Moyen-Orient, Afrique, Asie, Océanie, Amérique du Nord,
Amérique du Sud.

## 1. Où héberger ça gratuitement, sans carte bancaire

- **Hébergement de l'app** : [Render](https://render.com), offre "Free" — aucune carte
  bancaire demandée à l'inscription. Contrepartie : le service se met en veille après
  15 min d'inactivité et redémarre en quelques dizaines de secondes au prochain accès, et
  son disque n'est pas persistant.
- **Base de données** : [Neon](https://neon.tech) (Postgres géré), offre gratuite sans
  carte bancaire et sans expiration — c'est elle qui assure la vraie persistance des
  articles et bilans, puisque le disque de Render ne l'assure pas.
- **Réveil et déclenchement des tâches planifiées** : [cron-job.org](https://cron-job.org),
  gratuit et sans carte, vient réveiller l'app à intervalles réguliers et déclencher les
  collectes/bilans aux bonnes heures via l'API, pour compenser la mise en veille de Render.

## 2. Créer la base de données Neon

- Va sur https://neon.tech, crée un compte (email, sans carte bancaire).
- **Create a project** → choisis une région proche de toi.
- Une fois le projet créé, Neon affiche une **chaîne de connexion** du type
  `postgresql://user:password@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require` —
  copie-la, c'est ta `DATABASE_URL`.

## 3. Récupérer la clé API Gemini

Sur https://aistudio.google.com/apikey, connecte-toi avec un compte Google (aucune carte
requise) → **Create API key** → copie la clé.

## 4. Déployer sur Render

- Pousse ce projet sur un dépôt GitHub (Render déploie depuis un dépôt Git — voir section
  "Mettre le projet sur GitHub" ci-dessous si tu ne l'as pas encore fait).
- Sur https://render.com, crée un compte (email/GitHub, sans carte).
- **New → Web Service** → connecte ton dépôt GitHub `sentinel`.
- Configuration du service :
  - **Runtime** : Docker
  - **Dockerfile Path** : `backend/Dockerfile`
  - **Docker Build Context Directory** : `.` (racine du dépôt)
  - **Instance Type** : Free
- Dans **Environment**, ajoute les variables (mêmes noms que dans `.env.example`) :
  - `DATABASE_URL` (ta chaîne de connexion Neon)
  - `GEMINI_API_KEY`
  - `GEMINI_MODEL` = `gemini-2.5-flash`
  - `GEMINI_MIN_INTERVAL_SECONDS` = `4`
  - `SENTINEL_USERNAME` = `admin`
  - `SENTINEL_PASSWORD` = un mot de passe solide
  - `TIMEZONE` = `Europe/Paris`
  - `BRIEFING_TIMES` = `07:00,19:00`
  - `COLLECT_INTERVAL_MINUTES` = `30`
  - `CLASSIFY_BATCH_SIZE` = `10`
- **Create Web Service**. Render build l'image et te donne une URL du type
  `https://sentinel-xxxx.onrender.com`.

## 5. Compenser la mise en veille avec cron-job.org

Crée un compte gratuit sur https://cron-job.org (sans carte), puis crée ces tâches (
**Create cronjob**) :

- Une requête `GET https://sentinel-xxxx.onrender.com/api/health` toutes les 10 minutes,
  pour limiter les mises en veille pendant que tu consultes le dashboard.
- Une requête `POST https://sentinel-xxxx.onrender.com/api/collect` toutes les 30 minutes,
  pour déclencher la collecte + classification même si le service dormait.
- Une requête `POST https://sentinel-xxxx.onrender.com/api/briefings/generate-all` à 07:00
  et à 19:00, pour les bilans automatiques.

Ces trois routes sont protégées par l'authentification définie à l'étape précédente :
dans cron-job.org, section **Advanced → Authentication**, choisis **Basic Auth** et
renseigne `SENTINEL_USERNAME` / `SENTINEL_PASSWORD`.

## 6. Mettre le projet sur GitHub (si ce n'est pas déjà fait)

```bash
cd sentinel
git init
git add .
git commit -m "Sentinel géoveille"
```
Crée un nouveau dépôt (vide) sur https://github.com/new, puis :
```bash
git remote add origin https://github.com/<ton-compte>/sentinel.git
git branch -M main
git push -u origin main
```
Render se redéploiera automatiquement à chaque nouveau `git push` sur `main`.

## 7. Personnaliser les flux RSS

La liste des flux est dans `backend/app/feeds.py`, sous la forme :

```python
("Nom de la source", "https://url-du-flux.xml", "Zone par défaut", "Thème par défaut")
```

Sur Render, il n'y a pas de volume monté comme sur un serveur local : pour changer la
liste de flux, édite `backend/app/feeds.py` sur ton poste, puis :
```bash
git add backend/app/feeds.py
git commit -m "Mise à jour des flux"
git push
```
Render redéploie automatiquement à chaque push.

Certaines URLs de flux changent avec le temps ; si une source ne remonte plus rien après
quelques jours, vérifie son URL RSS actuelle sur le site de la source.

## 8. Fonctionnement

- **Collecteur** (`collector.py`) : interroge chaque flux, déduplique par URL, stocke les
  nouveaux articles en base avec le statut `new`.
- **Classifieur** (`classifier.py`) : pour chaque article `new`, demande à Gemini un JSON
  structuré (thème, zone, résumé français, score de pertinence, score de tension). Les
  articles jugés hors-sujet (score de pertinence faible) sont marqués `irrelevant` et
  n'apparaissent pas dans le fil.
- **Alertes** (`alerts.py`) : déclenchées soit par mots-clés sensibles (invasion, coup
  d'État, cyberattaque majeure...), soit par un score de tension élevé (seuil configurable
  via `ALERT_TENSION_THRESHOLD`).
- **Bilans** (`synthesizer.py`) : deux fois par jour (et à la demande), génère une synthèse
  Markdown par zone (dont une synthèse "Monde") à partir des articles classifiés depuis le
  bilan précédent.
- **Question libre** (`rag.py`) : recherche plein texte (SQLite FTS5) dans les articles
  stockés + filtre zone/thème, puis demande au LLM de répondre en s'appuyant uniquement sur
  ce contexte, avec les sources citées.

## 9. API

Le frontend consomme une API REST simple exposée par le même service (voir
`backend/app/main.py`), protégée par la même authentification que le dashboard :

- `GET /api/articles?zone=&theme=&hours=&limit=`
- `GET /api/briefings/latest`, `GET /api/briefings/history?zone=`
- `POST /api/briefings/generate?zone=Monde`, `POST /api/briefings/generate-all`
- `GET /api/alerts`
- `POST /api/ask` `{ "question": "...", "zone": "Europe" }`
- `POST /api/collect`, `POST /api/classify`
- `GET /api/stats`, `GET /api/health`

## 10. Limites connues / pistes d'amélioration

- **Mise en veille Render** : même avec le ping cron-job.org, un accès juste après une
  longue période creuse peut mettre quelques dizaines de secondes à répondre.
- **Quota Neon gratuit** : généreux pour ce volume d'articles (0,5 Go de stockage, largement
  suffisant), mais le projet peut se mettre en pause après une longue inactivité — un accès
  suffit à le réveiller automatiquement, avec un léger délai.
- La classification et les bilans dépendent du quota gratuit de l'API Gemini (limité en
  requêtes/minute et requêtes/jour) : en usage très intensif, tu peux atteindre ce quota —
  augmente `GEMINI_MIN_INTERVAL_SECONDS`/réduis `CLASSIFY_BATCH_SIZE` le cas échéant.
- Pas de scraping de pages sans flux RSS pour l'instant (volontairement laissé de côté pour
  rester simple et robuste).
- L'authentification est une Basic Auth simple : suffisante pour un usage personnel
  derrière HTTPS (Render fournit HTTPS automatiquement sur son sous-domaine `.onrender.com`),
  mais pas conçue pour du multi-utilisateur avec des rôles différents.
- Un seul modèle Gemini est utilisé pour classification, bilans et RAG ; tu peux faire
  pointer certaines étapes vers des modèles différents en éditant les appels dans
  `classifier.py` / `synthesizer.py` / `rag.py` si tu veux, par exemple, un modèle plus
  léger pour classer et un plus capable pour les bilans.

## 11. Tester en local avant de déployer

Avec Docker installé sur ton poste, `.env` rempli (voir `.env.example`, en pointant
`DATABASE_URL` vers ton projet Neon) :
```bash
docker compose up --build
```
Dashboard sur `http://localhost:8420`.
