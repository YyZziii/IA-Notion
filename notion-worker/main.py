import os
import sys
import time
import json
import redis
import subprocess
import shutil

# Forçage du mode non-bufferisé
os.environ["PYTHONUNBUFFERED"] = "1"
sys.stdout.reconfigure(line_buffering=True)

def debug(msg):
    print(msg)
    sys.stdout.flush()

debug("✅ Le script main.py a bien démarré")
debug("🔧 Démarrage du worker (avant connexion Redis)")

# Impression des variables d'environnement pour debug
debug("📦 Variables d'environnement :")
debug(f"  REDIS_URL      = {os.getenv('REDIS_URL')}")
debug(f"  QUEUE_NAME     = {os.getenv('QUEUE_NAME')}")
debug(f"  SYNC_IMAGE     = {os.getenv('SYNC_IMAGE')}")
debug(f"  DOCKER_NETWORK = {os.getenv('DOCKER_NETWORK')}")
debug(f"  NOTION_API_KEY = {'défini' if os.getenv('NOTION_API_KEY') else 'non défini'}")

# Vérifie si docker est disponible
if shutil.which("docker"):
    debug("🐳 La commande 'docker' est disponible")
else:
    debug("❌ La commande 'docker' est introuvable dans le conteneur")

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
QUEUE_NAME = os.getenv("QUEUE_NAME", "notion_events")
SYNC_IMAGE = os.getenv("SYNC_IMAGE", "notion-sync")
DOCKER_NETWORK = os.getenv("DOCKER_NETWORK", "open-webui-0520_default")

# Connexion Redis
try:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    debug("🔗 Connexion Redis réussie")
except Exception as e:
    debug(f"❌ Erreur de connexion Redis : {e}")
    time.sleep(10)
    exit(1)

debug("🚀 Notion Worker en attente d'événements...")

while True:
    try:
        _, raw_event = r.blpop(QUEUE_NAME)
        event = json.loads(raw_event)

        database_id = event.get("database_id")
        if not database_id:
            debug("⚠️  Aucune database_id dans l'événement. Ignoré.")
            continue

        debug(f"🧩 Événement reçu pour la base : {database_id}")

        container_name = f"notion-sync-run-{int(time.time())}"

        cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            "--network", DOCKER_NETWORK,
            "-e", f"NOTION_API_KEY={os.getenv('NOTION_API_KEY')}",
            "-e", f"NOTION_DATABASE_ID={database_id}",
            SYNC_IMAGE
        ]

        debug(f"📦 Lancement de la commande : {' '.join(cmd)}")
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        debug(f"✅ Synchronisation terminée pour : {database_id}")

    except Exception as e:
        debug(f"❌ Erreur dans le worker : {e}")
        time.sleep(5)
