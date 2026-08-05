#!/usr/bin/env python3
"""Exploration du schéma Agile dans Snowflake.

Sert à répondre à des questions ouvertes du cadrage :

1. Quel attribut `AGILE_FLEX` porte la **référence commerciale** d'un article ?
   (`--find-text`, `--exact`) — en pause, voir docs/01-contexte-et-besoin.md.
2. Quelle colonne / table porte le **cycle de vie** (« en production ») ?
   (`--list-lifecycle-columns`) — `Article.lifecycle` n'est rempli par aucune requête
   existante aujourd'hui.
3. La jointure CATEGORY/PRODUCT_LINES d'`agile_sync.ARTICLES_QUERY` renvoie-t-elle des
   libellés sensés, ou `NULL` silencieux partout ? (`--preview-sync`) — à vérifier avant
   tout premier `POST /api/sync` réel.

    python3 tools/discover_agile.py --item-number S1234567

Sans argument, le script liste les colonnes de la table ITEM et les ATTID les plus
fréquents sur les articles.
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "source"))

from catalogue.snowflake_client import connect, fetch_all  # noqa: E402

COLUMNS_QUERY = """
    SELECT COLUMN_NAME, DATA_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'AGILE' AND TABLE_NAME = '{table}'
    ORDER BY ORDINAL_POSITION
"""

# Plutôt que deviner des noms de table un par un : toute table portant une colonne liée à
# ATTID est une candidate pour la table de définition des attributs (nom, onglet...) —
# celle qui manque encore pour relier « Safran Sales Reference » à son numéro.
TABLES_WITH_ATTID_QUERY = """
    SELECT TABLE_NAME, COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'AGILE' AND COLUMN_NAME ILIKE '%ATT%ID%'
    ORDER BY TABLE_NAME
"""

ITEM_LOOKUP_QUERY = """
    SELECT ID, CLASS, ITEM_NUMBER, DESCRIPTION, DELETE_FLAG
    FROM ITEM
    WHERE ITEM_NUMBER = '{item_number}'
"""

# REV porte ses propres champs personnalisés en colonnes génériques (TEXT01..15,
# LIST01..25...), un système distinct d'AGILE_FLEX. La référence commerciale peut être
# rangée là plutôt que dans AGILE_FLEX — à vérifier en lisant les TEXTxx d'une révision.
REV_LOOKUP_QUERY = """
    SELECT r.ID, r.REV_NUMBER, r.LATEST_FLAG, r.DESCRIPTION,
           r.TEXT01, r.TEXT02, r.TEXT03, r.TEXT04, r.TEXT05,
           r.TEXT06, r.TEXT07, r.TEXT08, r.TEXT09, r.TEXT10,
           r.TEXT11, r.TEXT12, r.TEXT13, r.TEXT14, r.TEXT15
    FROM REV r
    JOIN ITEM i ON i.ID = r.ITEM
    WHERE i.ITEM_NUMBER = '{item_number}'
    ORDER BY r.LATEST_FLAG DESC
"""

# af.ID seul n'est pas une clé fiable : sans le filtre de classe, la jointure ramène des
# attributs d'objets sans rapport (BOM, étiquettes...) dont l'ID numérique coïncide avec
# celui de l'article. Vérifié en conditions réelles sur S110647.
FLEX_FOR_ITEM_QUERY = """
    SELECT af.ATTID, af.ROW_ID, af.TEXT
    FROM AGILE_FLEX af
    JOIN ITEM i ON i.ID = af.ID AND i.CLASS = af.CLASS
    WHERE i.ITEM_NUMBER = '{item_number}'
      AND af.TEXT IS NOT NULL
    ORDER BY af.ID = af.ROW_ID DESC, af.ATTID
"""

# Recherche directe d'un texte connu (ex. une référence commerciale déjà lue dans le
# classeur) dans AGILE_FLEX, sans dépendre d'une hypothèse sur la jointure ITEM/ID : si le
# texte existe quelque part, son ATTID est la réponse cherchée, quel que soit l'article.
FIND_TEXT_QUERY = """
    SELECT af.ATTID, af.TEXT, i.ITEM_NUMBER
    FROM AGILE_FLEX af
    JOIN ITEM i ON i.ID = af.ID AND i.CLASS = af.CLASS
    WHERE af.TEXT ILIKE '%{needle}%'
    LIMIT 20
"""

# Une correspondance partielle peut confondre la référence commerciale avec la désignation
# complète qui la contient (« CRT-Q-EXT-4U » est un sous-texte de « CRT-Q-EXT-4U+P3U ») :
# l'égalité stricte lève l'ambiguïté.
FIND_EXACT_QUERY = """
    SELECT af.ATTID, af.TEXT, i.ITEM_NUMBER
    FROM AGILE_FLEX af
    JOIN ITEM i ON i.ID = af.ID AND i.CLASS = af.CLASS
    WHERE af.TEXT = '{needle}'
    LIMIT 20
"""

FLEX_ATTID_FREQUENCY_QUERY = """
    SELECT af.ATTID, COUNT(*) AS N, ANY_VALUE(af.TEXT) AS SAMPLE_TEXT
    FROM AGILE_FLEX af
    WHERE af.CLASS = 10000
      AND af.ID = af.ROW_ID
      AND af.TEXT IS NOT NULL
    GROUP BY af.ATTID
    ORDER BY N DESC
    LIMIT 40
"""

SAMPLE_ITEMS_QUERY = """
    SELECT i.ITEM_NUMBER, i.DESCRIPTION
    FROM ITEM i
    WHERE i.CLASS = 10000
      AND (i.DELETE_FLAG IS NULL OR i.DELETE_FLAG != 1)
    LIMIT 10
"""

# Reprend exactement la jointure d'agile_sync.ARTICLES_QUERY, mais en gardant les colonnes
# brutes (CATEGORY, PRODUCT_LINES) à côté du libellé joint : sans ça, une jointure qui ne
# matche jamais rend juste NULL partout, silencieusement — rien ne le distingue d'une vraie
# absence de catégorie. Jamais vérifié sur de vraies données avant ce tour.
SYNC_PREVIEW_QUERY = """
    SELECT
        i.ITEM_NUMBER, i.DESCRIPTION,
        i.CATEGORY, le_cat.ENTRYVALUE AS CATEGORY_LABEL,
        i.PRODUCT_LINES, le_pl.ENTRYVALUE AS PRODUCT_LINE_LABEL
    FROM ITEM i
    LEFT JOIN LISTENTRY le_cat
           ON le_cat.ENTRYID = i.CATEGORY AND le_cat.LANGID = 3
    LEFT JOIN LISTENTRY le_pl
           ON le_pl.ENTRYID = TRY_CAST(SPLIT_PART(i.PRODUCT_LINES, ',', 2) AS NUMBER)
          AND le_pl.LANGID = 3
    WHERE i.CLASS = 10000
      AND (i.DELETE_FLAG IS NULL OR i.DELETE_FLAG != 1)
    LIMIT 15
"""

# `Article.lifecycle` (models.py) n'est rempli par aucune requête existante — jamais
# implémenté. Cherche toute colonne du schéma AGILE dont le nom évoque un statut de cycle
# de vie, candidate pour combler ce champ.
LIFECYCLE_COLUMNS_QUERY = """
    SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'AGILE'
      AND (COLUMN_NAME ILIKE '%LIFECYCLE%' OR COLUMN_NAME ILIKE '%STATUS%'
           OR COLUMN_NAME ILIKE '%PHASE%' OR COLUMN_NAME ILIKE '%STATE%'
           OR COLUMN_NAME ILIKE '%RELEASE%')
    ORDER BY TABLE_NAME, COLUMN_NAME
"""


def show(title: str, rows: list[dict]) -> None:
    print(f"\n=== {title} ===")
    if not rows:
        print("(aucun résultat)")
        return
    for row in rows:
        print("  " + " | ".join(f"{k}={v}" for k, v in row.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item-number", help="Article de référence à inspecter en détail")
    parser.add_argument(
        "--find-text",
        help="Cherche ce texte dans AGILE_FLEX.TEXT (ex. une référence commerciale connue) "
             "pour trouver son ATTID, sans dépendre de la jointure sur un article précis",
    )
    parser.add_argument(
        "--exact", action="store_true",
        help="Avec --find-text : égalité stricte plutôt que sous-chaîne, pour ne pas "
             "confondre une référence commerciale avec la désignation qui la contient",
    )
    parser.add_argument(
        "--table", default="ITEM", help="Table dont on veut les colonnes (défaut : ITEM)"
    )
    parser.add_argument(
        "--list-attid-tables", action="store_true",
        help="Liste toutes les tables du schéma AGILE portant une colonne liée à ATTID "
             "(candidates pour la table de définition des attributs)",
    )
    parser.add_argument(
        "--preview-sync", action="store_true",
        help="Rejoue la jointure CATEGORY/PRODUCT_LINES d'agile_sync.ARTICLES_QUERY sur "
             "15 articles, colonnes brutes et libellés joints côte à côte — à vérifier "
             "avant de lancer POST /api/sync pour de vrai.",
    )
    parser.add_argument(
        "--list-lifecycle-columns", action="store_true",
        help="Cherche les colonnes du schéma AGILE dont le nom évoque un cycle de vie "
             "(Article.lifecycle n'est rempli par aucune requête existante).",
    )
    args = parser.parse_args()

    if not os.getenv("SNOWFLAKE_USER"):
        sys.exit("Renseigner le .env (SNOWFLAKE_USER, SNOWFLAKE_PRIVATE_KEY_FILE…) d'abord.")

    conn = connect()
    try:
        if args.list_attid_tables:
            show("Tables avec une colonne liée à ATTID", fetch_all(conn, TABLES_WITH_ATTID_QUERY))
            return
        if args.preview_sync:
            show("Aperçu de la jointure CATEGORY/PRODUCT_LINES (agile_sync.ARTICLES_QUERY)",
                 fetch_all(conn, SYNC_PREVIEW_QUERY))
            return
        if args.list_lifecycle_columns:
            show("Colonnes évoquant un cycle de vie", fetch_all(conn, LIFECYCLE_COLUMNS_QUERY))
            return
        if args.find_text:
            query, verb = (FIND_EXACT_QUERY, "égal à") if args.exact else (FIND_TEXT_QUERY, "contenant")
            show(f"AGILE_FLEX {verb} « {args.find_text} »",
                 fetch_all(conn, query, needle=args.find_text))
            return
        show(f"Colonnes de {args.table}", fetch_all(conn, COLUMNS_QUERY, table=args.table))
        show("Exemples d'articles", fetch_all(conn, SAMPLE_ITEMS_QUERY))
        if args.item_number:
            show(f"Fiche ITEM {args.item_number}",
                 fetch_all(conn, ITEM_LOOKUP_QUERY, item_number=args.item_number))
            show(f"Révisions REV de {args.item_number} (colonnes TEXTxx)",
                 fetch_all(conn, REV_LOOKUP_QUERY, item_number=args.item_number))
            show(
                f"Attributs AGILE_FLEX de {args.item_number} (toutes révisions)",
                fetch_all(conn, FLEX_FOR_ITEM_QUERY, item_number=args.item_number),
            )
        else:
            show("ATTID les plus fréquents (classe 10000)", fetch_all(conn, FLEX_ATTID_FREQUENCY_QUERY))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
