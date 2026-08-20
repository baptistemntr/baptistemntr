"""Comparaison de la grille (IMI) à la liste de vente officielle Agile.

Un article Agile (« LISTE PRODUITS <gamme> », ex. S113459 pour CRT) recense, via sa
nomenclature (BOM), les codes articles réellement vendus pour une gamme — repéré à partir
de S113472 (« LISTE VENTE PRODUITS LES ULIS »), qui liste une sous-liste par gamme dans sa
propre nomenclature (voir tools/discover_agile.py --find-list-tables /--bom-of pour rejouer
l'exploration). Un article de grille absent de cette liste est en général retiré côté Agile
(évolution, obsolescence) — signalé pour relecture, jamais supprimé automatiquement, même
philosophie que bom_check.py.

Une gamme peut avoir plusieurs listes (HDR en a 3 : « LISTE PRODUITS HDR PCC », « ... HDR
4G », « ... HDR 4GPLUS ») — matchées par préfixe de désignation et union-nées. Le nom de
gamme Agile ne recoupe pas toujours exactement notre code (ex. notre RSR-RF s'appelle juste
« RSR » côté Agile) : le résultat expose toujours les listes trouvées pour que l'IMI
vérifie que c'est la bonne avant de lire les écarts.
"""

from catalogue.database import SessionLocal
from catalogue.models import ArticleMapping
from catalogue.snowflake_client import connect, fetch_all

_LIST_PREFIX = "LISTE PRODUITS"

# ILIKE plutôt qu'une jointure sur un identifiant : il n'existe aucun champ Agile reliant
# une gamme catalogue à sa liste de vente (même constat que pour la gamme elle-même, voir
# docs/06-admin-imi.md § Créer une gamme) — seule la désignation, saisie à la main côté
# Agile, porte cette information.
FIND_SALE_LISTS_QUERY = """
    SELECT ITEM_NUMBER, DESCRIPTION
    FROM ITEM
    WHERE DESCRIPTION ILIKE 'LISTE PRODUITS {code}%'
      AND (DELETE_FLAG IS NULL OR DELETE_FLAG != 1)
"""

# Même jointure que bom_check.BOM_FOR_ITEMS_QUERY (validée sur S128354) : BOM.ITEM est le
# parent (résolu via ITEM.ID), CHANGE_OUT = 0 filtre les lignes actives.
BOM_FOR_ITEMS_QUERY = """
    SELECT parent.ITEM_NUMBER AS PARENT_ITEM_NUMBER,
           comp.ITEM_NUMBER AS COMPONENT_ITEM_NUMBER,
           comp.DESCRIPTION AS COMPONENT_DESCRIPTION
    FROM BOM b
    JOIN ITEM parent ON parent.ID = b.ITEM
    JOIN ITEM comp ON comp.ID = b.COMPONENT
    WHERE parent.ITEM_NUMBER IN ({item_numbers})
      AND b.CHANGE_OUT = 0
"""


def check_family(family_code: str) -> dict:
    """Compare les codes articles de la grille d'une gamme à sa liste de vente Agile.

    Renvoie les listes de vente trouvées (à vérifier par l'IMI), les articles de grille
    absents de leur union, et une note explicative quand la comparaison n'a pas pu avoir
    lieu (pas de code Agile en grille, ou aucune liste trouvée pour cette gamme).
    """
    session = SessionLocal()
    try:
        mappings = (
            session.query(ArticleMapping)
            .filter(ArticleMapping.family_code == family_code, ArticleMapping.item_number.isnot(None))
            .all()
        )
        our_items = {m.item_number: m.designation for m in mappings}
    finally:
        session.close()

    if not our_items:
        return {
            "sale_lists": [], "missing": [],
            "note": "Aucun article avec un code Agile dans la grille de cette gamme.",
        }

    conn = connect()
    try:
        quoted_code = family_code.replace("'", "''")
        lists = fetch_all(conn, FIND_SALE_LISTS_QUERY.format(code=quoted_code))
        if not lists:
            return {
                "sale_lists": [], "missing": [],
                "note": f"Aucune liste Agile « LISTE PRODUITS {family_code}… » trouvée — le "
                        "nom de gamme Agile diffère peut-être du nôtre (voir docs/06-admin-imi.md).",
            }

        # Un composant dont la désignation commence aussi par "LISTE PRODUITS" est une
        # sous-liste imbriquée (ex. "LISTE PRODUITS CRT PCC SECU" dans "LISTE PRODUITS
        # CRT"), pas un article vendable : on la déplie plutôt que de la compter comme un
        # article manquant. `seen` évite de reboucler si une sous-liste se référence.
        sale_list_labels = {row["ITEM_NUMBER"]: row["DESCRIPTION"] for row in lists}
        to_expand = list(sale_list_labels)
        seen = set()
        sold_items: dict[str, str | None] = {}
        while to_expand:
            quoted = ", ".join(f"'{n}'" for n in to_expand)
            rows = fetch_all(conn, BOM_FOR_ITEMS_QUERY.format(item_numbers=quoted))
            seen.update(to_expand)
            to_expand = []
            for row in rows:
                code, desc = row["COMPONENT_ITEM_NUMBER"], row["COMPONENT_DESCRIPTION"]
                if desc and desc.upper().startswith(_LIST_PREFIX):
                    if code not in seen:
                        to_expand.append(code)
                else:
                    sold_items[code] = desc
    finally:
        conn.close()

    missing = sorted(
        ({"item_number": code, "designation": our_items[code]}
         for code in our_items if code not in sold_items),
        key=lambda d: d["item_number"],
    )
    return {
        "sale_lists": [{"item_number": k, "description": v} for k, v in sale_list_labels.items()],
        "missing": missing,
        "note": None,
    }
