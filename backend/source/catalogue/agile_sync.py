"""Synchronisation descendante Agile → miroir local des articles.

Agile est la source de vérité pour les articles (code, désignation, ligne produit).
Il ne l'est jamais pour la configuration du catalogue, qui appartient à l'IMI.
"""

import os
from datetime import datetime, timezone

from catalogue.database import SessionLocal
from catalogue.models import Article
from catalogue.snowflake_client import connect, fetch_all

# Classe Agile des articles (« Pièces »). Les documents (9000) ne concernent pas le catalogue.
ITEM_CLASS_PART = 10000

# Valeur d'ITEM.SUBCLASS trouvée sur les 7 articles finis de référence connus
# (tools/discover_agile.py --probe-subclass-raw), pas résolvable en libellé via LISTENTRY
# (aucune entrée pour cet ENTRYID) — d'où la comparaison à la valeur numérique brute plutôt
# qu'à un libellé. IS_TLA, censé porter la même distinction, s'est révélé entièrement vide.
FINISHED_GOOD_SUBCLASS = 2472645

# ATTID de l'attribut AGILE_FLEX portant la référence commerciale.
# À renseigner une fois identifié avec tools/discover_agile.py.
COMMERCIAL_REF_ATTID = os.getenv("AGILE_COMMERCIAL_REF_ATTID", "")

# Jointure vérifiée sur de vraies données (tools/discover_agile.py --preview-sync) : les
# libellés CATEGORY/PRODUCT_LINE sont correctement résolus, pas de NULL silencieux.
ARTICLES_QUERY = f"""
    SELECT
        i.ID            AS ITEM_ID,
        i.ITEM_NUMBER   AS ITEM_NUMBER,
        i.DESCRIPTION   AS DESCRIPTION,
        i.SUBCLASS      AS SUBCLASS,
        le_cat.ENTRYVALUE AS CATEGORY_LABEL,
        le_pl.ENTRYVALUE  AS PRODUCT_LINE_LABEL
    FROM ITEM i
    LEFT JOIN LISTENTRY le_cat
           ON le_cat.ENTRYID = i.CATEGORY AND le_cat.LANGID = 3
    LEFT JOIN LISTENTRY le_pl
           ON le_pl.ENTRYID = TRY_CAST(SPLIT_PART(i.PRODUCT_LINES, ',', 2) AS NUMBER)
          AND le_pl.LANGID = 3
    WHERE i.CLASS = {ITEM_CLASS_PART}
      AND (i.DELETE_FLAG IS NULL OR i.DELETE_FLAG != 1)
"""

COMMERCIAL_REF_QUERY = """
    SELECT af.ID AS ITEM_ID, af.TEXT AS COMMERCIAL_REF
    FROM AGILE_FLEX af
    WHERE af.ID = af.ROW_ID
      AND af.CLASS = 10000
      AND af.ATTID = {attid}
"""


def sync_articles() -> dict:
    """Rafraîchit le miroir local des articles. Renvoie un compte-rendu de synchro."""
    conn = connect()
    try:
        rows = fetch_all(conn, ARTICLES_QUERY)
        refs: dict[str, str] = {}
        if COMMERCIAL_REF_ATTID:
            for row in fetch_all(conn, COMMERCIAL_REF_QUERY, attid=COMMERCIAL_REF_ATTID):
                refs[str(int(row["ITEM_ID"]))] = row["COMMERCIAL_REF"]
    finally:
        conn.close()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    created = updated = 0
    session = SessionLocal()
    try:
        for row in rows:
            item_number = row["ITEM_NUMBER"]
            if not item_number:
                continue
            article = session.get(Article, item_number)
            if article is None:
                article = Article(item_number=item_number)
                session.add(article)
                created += 1
            else:
                updated += 1
            article.description = row.get("DESCRIPTION")
            article.category = row.get("CATEGORY_LABEL")
            article.product_line = row.get("PRODUCT_LINE_LABEL")
            subclass = row.get("SUBCLASS")
            article.is_finished_good = subclass == FINISHED_GOOD_SUBCLASS if subclass is not None else None
            article.commercial_ref = refs.get(str(int(row["ITEM_ID"]))) or article.commercial_ref
            # article.lifecycle n'est jamais renseigné : trois pistes explorées sans succès
            # (VERSION.LIFECYCLEPHASE, REV.RELEASE_TYPE, CHANGE.STATUSTYPE — voir
            # docs/01-contexte-et-besoin.md § 5 et tools/discover_agile.py --probe-lifecycle).
            # Reste `None` plutôt que d'afficher une valeur devinée.
            article.last_sync = now
        session.commit()
    finally:
        session.close()

    return {"fetched": len(rows), "created": created, "updated": updated, "synced_at": now}
