# Catalogue Industriel — image unique : le serveur (FastAPI) sert aussi le site statique
# (frontend/), donc un seul conteneur suffit. Voir docs/02-architecture.md pour le détail
# de l'architecture, et le README pour le lancement sans Docker.

FROM python:3.11-slim

# Décommenter si l'installation des dépendances échoue faute de roue précompilée pour
# cette plateforme (rare — snowflake-connector-python et psycopg2-binary fournissent des
# roues manylinux pour les cas courants) :
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential libssl-dev \
#     && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

COPY backend/requirements.txt backend/pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# `pip install -e .` a besoin du code source déjà présent (setuptools le découvre à
# l'installation) — copié avant, pas après, sinon l'installation échoue silencieusement.
COPY backend/source ./source
RUN pip install --no-cache-dir -e .

COPY frontend /app/frontend

ENV PYTHONPATH=source

EXPOSE 8010

# Le fichier .env et le dossier secrets/ (clé Snowflake) ne sont jamais copiés dans
# l'image — ce sont des secrets, à monter au lancement (voir docker-compose.yml ou
# `docker run -v`). Sans eux, le serveur démarre quand même (mode dégradé, sans Agile).
CMD ["python", "-m", "uvicorn", "catalogue.server:app", "--host", "0.0.0.0", "--port", "8010"]
