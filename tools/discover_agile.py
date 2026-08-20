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
4. La nomenclature (BOM) d'un article contient-elle bien les composants attendus des
   options cochées pour lui dans la grille ? (`--bom-of`) — prépare une détection
   d'incohérences grille ↔ Agile, voir docs/01-contexte-et-besoin.md.

    python3 tools/discover_agile.py --item-number S1234567
    python3 tools/discover_agile.py --bom-of S128354

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
# RELEASED/RELEASE_TYPE/RELEASE_DATE : candidats pour Article.lifecycle (VERSION, trouvé
# par --list-lifecycle-columns, s'est avéré être du versionnage de pièces jointes/documents
# — ATTACH_ID, LABEL, REVISION — pas le cycle de vie de l'article ; faux positif écarté).
REV_LOOKUP_QUERY = """
    SELECT r.ID, r.REV_NUMBER, r.LATEST_FLAG, r.DESCRIPTION,
           r.RELEASED, r.RELEASE_TYPE, r.OLD_RELEASE_TYPE, r.RELEASE_DATE,
           r.TEXT01, r.TEXT02, r.TEXT03, r.TEXT04, r.TEXT05,
           r.TEXT06, r.TEXT07, r.TEXT08, r.TEXT09, r.TEXT10,
           r.TEXT11, r.TEXT12, r.TEXT13, r.TEXT14, r.TEXT15
    FROM REV r
    JOIN ITEM i ON i.ID = r.ITEM
    WHERE i.ITEM_NUMBER = '{item_number}'
    ORDER BY r.LATEST_FLAG DESC
"""

# RELEASE_TYPE/OLD_RELEASE_TYPE ressemblent à des ENTRYID (même système que
# CATEGORY/PRODUCT_LINES sur ITEM) : un code numérique qui pointe vers LISTENTRY pour un
# libellé humain (« Production », « Obsolète »...) plutôt qu'une valeur directement lisible.
REV_RELEASE_TYPE_QUERY = """
    SELECT r.REV_NUMBER, r.LATEST_FLAG, r.RELEASED, r.RELEASE_DATE,
           r.RELEASE_TYPE, le_rt.ENTRYVALUE AS RELEASE_TYPE_LABEL,
           r.OLD_RELEASE_TYPE, le_ort.ENTRYVALUE AS OLD_RELEASE_TYPE_LABEL
    FROM REV r
    JOIN ITEM i ON i.ID = r.ITEM
    LEFT JOIN LISTENTRY le_rt ON le_rt.ENTRYID = r.RELEASE_TYPE AND le_rt.LANGID = 3
    LEFT JOIN LISTENTRY le_ort ON le_ort.ENTRYID = r.OLD_RELEASE_TYPE AND le_ort.LANGID = 3
    WHERE i.ITEM_NUMBER = '{item_number}'
    ORDER BY r.LATEST_FLAG DESC
"""

# Sur S128362, la jointure LISTENTRY (n'importe quelle langue) n'a rien donné pour
# RELEASE_TYPE=2472980/2472981 : à vérifier si ces ENTRYID existent seulement sous une autre
# langue, ou pas du tout dans LISTENTRY (auquel cas RELEASE_TYPE référence autre chose).
RELEASE_TYPE_RAW_QUERY = """
    SELECT * FROM LISTENTRY WHERE ENTRYID IN (2472980, 2472981)
"""

# Hypothèse alternative : le cycle de vie vient du processus de changement (ECO), pas d'une
# liste sur REV. ITEM.LATEST_RELEASED_ECO/DEFAULT_CHANGE pointent potentiellement vers
# CHANGE, dont STATUS/STATUSTYPE (trouvés par --list-lifecycle-columns) portent un état.
CHANGE_LOOKUP_QUERY = """
    SELECT i.LATEST_RELEASED_ECO, i.DEFAULT_CHANGE,
           c.STATUS, c.STATUSTYPE, ls.ENTRYVALUE AS STATUSTYPE_LABEL
    FROM ITEM i
    LEFT JOIN CHANGE c ON c.ID = i.LATEST_RELEASED_ECO
    LEFT JOIN LISTENTRY ls ON ls.ENTRYID = c.STATUSTYPE AND ls.LANGID = 3
    WHERE i.ITEM_NUMBER = '{item_number}'
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

# Teste si ITEM.IS_TLA (« Top Level Assembly ») isole les articles finis/vendables des
# pièces brutes (vis, câbles...) qui composent la grande majorité de la classe 10000 —
# hypothèse pour réduire le bruit d'une éventuelle extraction de préfixe de gamme depuis
# DESCRIPTION (ex. « CRT-Q-EXT-4U » → CRT), déjà vérifiée peu fiable telle quelle (HDR,
# SATCORE portent un nom commercial différent : « CORTEX », « SATEL.MODEM »). IS_TLA ne
# réglera pas ce problème de nommage, seulement — si l'hypothèse se vérifie — le volume de
# bruit à filtrer avant d'en tirer un préfixe.
TLA_DISTRIBUTION_QUERY = """
    SELECT IS_TLA, COUNT(*) AS N
    FROM ITEM
    WHERE CLASS = 10000
    GROUP BY IS_TLA
    ORDER BY N DESC
"""

TLA_KNOWN_ITEMS_QUERY = """
    SELECT ITEM_NUMBER, DESCRIPTION, IS_TLA
    FROM ITEM
    WHERE ITEM_NUMBER IN ({item_numbers})
"""

TLA_SAMPLE_QUERY = """
    SELECT ITEM_NUMBER, DESCRIPTION
    FROM ITEM
    WHERE CLASS = 10000
      AND IS_TLA = 1
      AND (DELETE_FLAG IS NULL OR DELETE_FLAG != 1)
    ORDER BY RANDOM()
    LIMIT 30
"""

# Piste non testée : ITEM.CATEGORY (résolu en CATEGORY_LABEL via LISTENTRY, déjà utilisé par
# agile_sync.ARTICLES_QUERY -> Article.category) est un champ distinct de PRODUCT_LINES,
# jamais vérifié pour la granularité gamme (CRT/HDR/SATCORE). Contrairement au préfixe de
# DESCRIPTION (fiable sur 4/6 seulement) et à IS_TLA (vide), CATEGORY est une vraie colonne
# de classification Agile — reste à voir si ses valeurs distinctes ressemblent à des gammes
# ou sont aussi larges que PRODUCT_LINES (ex. « ARC S&C »).
CATEGORY_DISTRIBUTION_QUERY = """
    SELECT le_cat.ENTRYVALUE AS CATEGORY_LABEL, COUNT(*) AS N
    FROM ITEM i
    LEFT JOIN LISTENTRY le_cat
           ON le_cat.ENTRYID = i.CATEGORY AND le_cat.LANGID = 3
    WHERE i.CLASS = 10000
      AND (i.DELETE_FLAG IS NULL OR i.DELETE_FLAG != 1)
    GROUP BY le_cat.ENTRYVALUE
    ORDER BY N DESC
    LIMIT 60
"""

CATEGORY_KNOWN_ITEMS_QUERY = """
    SELECT i.ITEM_NUMBER, i.DESCRIPTION, le_cat.ENTRYVALUE AS CATEGORY_LABEL
    FROM ITEM i
    LEFT JOIN LISTENTRY le_cat
           ON le_cat.ENTRYID = i.CATEGORY AND le_cat.LANGID = 3
    WHERE i.ITEM_NUMBER IN ({item_numbers})
"""

# Sert à vérifier une hypothèse pour une future détection d'incohérences grille ↔ Agile
# (docs/01-contexte-et-besoin.md) : Option.component_item_number (ex. S128865 pour l'option
# C0 de CRT) doit apparaître dans la nomenclature réelle de l'article que la grille associe
# à cette option (ex. S128354 = CRT, C0 + 4U). BOM.ITEM (numérique) est le parent, à
# résoudre via ITEM.ID — PAS BOM.ITEM_NUMBER, qui pointe vers un autre article : une
# première version de cette requête filtrant sur BOM.ITEM_NUMBER = 'S128354' a renvoyé une
# unique ligne auto-référente (composant = S128354 lui-même), signe que la colonne
# identifie en réalité la ligne où S128354 est *utilisé comme composant* d'un autre
# article, pas sa propre composition. BOM.COMPONENT est l'ID interne de l'enfant, à
# résoudre via ITEM.ID lui aussi. CHANGE_OUT = 0 signale la ligne active : les
# nomenclatures sont historisées via ECO, une ligne remplacée reste en base.
BOM_FOR_ITEM_QUERY = """
    SELECT
        b.FIND_NUMBER, b.SEQ, b.QUANTITY,
        comp.ITEM_NUMBER AS COMPONENT_ITEM_NUMBER, comp.DESCRIPTION AS COMPONENT_DESCRIPTION
    FROM BOM b
    JOIN ITEM parent ON parent.ID = b.ITEM
    JOIN ITEM comp ON comp.ID = b.COMPONENT
    WHERE parent.ITEM_NUMBER = '{item_number}'
      AND b.CHANGE_OUT = 0
    ORDER BY b.SEQ
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
    parser.add_argument(
        "--probe-lifecycle",
        help="Sur l'article donné : vérifie si RELEASE_TYPE existe dans LISTENTRY (toute "
             "langue), et si ITEM.LATEST_RELEASED_ECO/DEFAULT_CHANGE mène à un statut via "
             "CHANGE — deux hypothèses concurrentes après l'échec de la jointure LANGID=3.",
    )
    parser.add_argument(
        "--bom-of",
        help="Liste la nomenclature active (BOM, CHANGE_OUT=0) d'un article, composant par "
             "composant — pour vérifier la correspondance avec Option.component_item_number "
             "(ex. S128354 doit contenir S128865, le composant de l'option C0 côté CRT).",
    )
    parser.add_argument(
        "--probe-tla", action="store_true",
        help="Teste si ITEM.IS_TLA isole les articles finis des pièces brutes : "
             "distribution des valeurs, IS_TLA des 6 articles de gamme connus, échantillon "
             "de désignations parmi IS_TLA=1.",
    )
    parser.add_argument(
        "--probe-category", action="store_true",
        help="Teste si ITEM.CATEGORY (résolu en CATEGORY_LABEL, déjà utilisé par "
             "Article.category) recoupe la granularité gamme : distribution des libellés "
             "distincts, CATEGORY_LABEL des 6 articles de gamme connus.",
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
        if args.probe_lifecycle:
            show("LISTENTRY pour ENTRYID 2472980/2472981 (toute langue)",
                 fetch_all(conn, RELEASE_TYPE_RAW_QUERY))
            show(f"CHANGE lié à {args.probe_lifecycle} via LATEST_RELEASED_ECO/DEFAULT_CHANGE",
                 fetch_all(conn, CHANGE_LOOKUP_QUERY, item_number=args.probe_lifecycle))
            return
        if args.bom_of:
            show(f"Nomenclature active (BOM) de {args.bom_of}",
                 fetch_all(conn, BOM_FOR_ITEM_QUERY, item_number=args.bom_of))
            return
        if args.probe_tla:
            show("Distribution de IS_TLA (classe 10000)", fetch_all(conn, TLA_DISTRIBUTION_QUERY))
            # Les 6 articles déjà utilisés pour tester l'extraction de préfixe de gamme
            # (CRT, HDR, SATCORE, DTR, RSR-RF, WBR) — pour voir si IS_TLA les identifie tous
            # comme finis, ou si le signal est incohérent même sur des cas connus.
            known = "'S110647', 'S100683', 'S100681', 'S128362', 'S135963', 'S122464'"
            show("IS_TLA des 6 articles de gamme connus",
                 fetch_all(conn, TLA_KNOWN_ITEMS_QUERY.format(item_numbers=known)))
            show("Échantillon aléatoire de 30 désignations parmi IS_TLA=1",
                 fetch_all(conn, TLA_SAMPLE_QUERY))
            return
        if args.probe_category:
            show("Distribution de CATEGORY_LABEL (classe 10000)",
                 fetch_all(conn, CATEGORY_DISTRIBUTION_QUERY))
            known = "'S110647', 'S100683', 'S100681', 'S128362', 'S135963', 'S122464'"
            show("CATEGORY_LABEL des 6 articles de gamme connus",
                 fetch_all(conn, CATEGORY_KNOWN_ITEMS_QUERY.format(item_numbers=known)))
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
            show(f"RELEASE_TYPE / OLD_RELEASE_TYPE de {args.item_number} (libellés LISTENTRY)",
                 fetch_all(conn, REV_RELEASE_TYPE_QUERY, item_number=args.item_number))
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
