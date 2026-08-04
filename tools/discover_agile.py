#!/usr/bin/env python3
"""Exploration du schéma Agile dans Snowflake.

Sert à répondre à deux questions ouvertes du cadrage :

1. Quel attribut `AGILE_FLEX` porte la **référence commerciale** d'un article ?
2. Quelle colonne / table porte le **cycle de vie** (« en production ») ?

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

ITEM_LOOKUP_QUERY = """
    SELECT ID, CLASS, ITEM_NUMBER, DESCRIPTION, DELETE_FLAG
    FROM ITEM
    WHERE ITEM_NUMBER = '{item_number}'
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
    args = parser.parse_args()

    if not os.getenv("SNOWFLAKE_USER"):
        sys.exit("Renseigner le .env (SNOWFLAKE_USER, SNOWFLAKE_PRIVATE_KEY_FILE…) d'abord.")

    conn = connect()
    try:
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
