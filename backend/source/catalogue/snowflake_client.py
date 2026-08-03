"""Connexion Snowflake vers le PLM Agile.

Reprend à l'identique la configuration de l'agent Agile déjà en production :
authentification par paire de clés RSA sur le compte de service GS3_SERVICE_USER.
"""

import os

SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT", "safran-sed_space")
SNOWFLAKE_HOST = os.getenv(
    "SNOWFLAKE_HOST", "safran-sed_space.privatelink.snowflakecomputing.com"
)
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER", "")
SNOWFLAKE_PRIVATE_KEY_FILE = os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE", "")
SNOWFLAKE_PRIVATE_KEY_PWD = os.getenv("SNOWFLAKE_PRIVATE_KEY_PWD", "")
SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE", "RF_GS3_ANALYST")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "WH_GS3")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "PRD_RAW_PLM_AGILE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "AGILE")


def is_configured() -> bool:
    """Indique si les identifiants Snowflake sont disponibles.

    Permet à l'API de démarrer en mode dégradé (catalogue local uniquement) sur un poste
    de développement sans accès au PLM.
    """
    return bool(SNOWFLAKE_USER and SNOWFLAKE_PRIVATE_KEY_FILE)


def connect():
    if not is_configured():
        raise RuntimeError(
            "SNOWFLAKE_USER / SNOWFLAKE_PRIVATE_KEY_FILE absents de l'environnement"
        )
    # Import tardif : l'API doit pouvoir démarrer sur un poste sans le connecteur installé.
    import snowflake.connector

    return snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        host=SNOWFLAKE_HOST,
        user=SNOWFLAKE_USER,
        private_key_file=SNOWFLAKE_PRIVATE_KEY_FILE,
        private_key_file_pwd=SNOWFLAKE_PRIVATE_KEY_PWD or None,
        role=SNOWFLAKE_ROLE,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
        login_timeout=30,
        # Le certificat interne Safran n'est pas reconnu par le magasin par défaut.
        insecure_mode=True,
    )


def fetch_all(conn, query: str, **params) -> list[dict]:
    """Exécute une requête et renvoie les lignes sous forme de dictionnaires."""
    cur = conn.cursor()
    cur.execute(query.format(**params) if params else query)
    columns = [col[0] for col in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]
