"""Détection d'incohérences entre la grille (IMI) et la nomenclature réelle Agile (BOM).

Compare, pour chaque ligne de grille d'une gamme, les `Option.component_item_number` des
options cochées avec les composants réellement présents dans la nomenclature active de
l'article Agile associé. Signale un écart, ne corrige jamais rien — même philosophie que
`tools/import_workbook.py` pour le classeur (voir `docs/05-diagnostic-classeur.md`).

Une valeur absente n'est pas forcément une erreur de grille : le composant réel d'une
option peut varier selon une autre option cochée à côté (ex. l'option C0 de CRT vaut
S128865 en châssis 2U mais S144191 en 4U — les deux sont de vrais modules actifs, la
grille n'a capturé qu'un seul exemple). Le résultat est un rapport à relire par l'IMI, pas
un verdict automatique — voir `docs/01-contexte-et-besoin.md`.
"""

import re

from catalogue.database import SessionLocal
from catalogue.models import ArticleMapping
from catalogue.snowflake_client import connect, fetch_all

# Une partie des component_item_number recopiés du classeur ne sont pas de vrais codes
# Agile mais du texte libre (« S120657+cables+meca », « 3 * S119519 ») : vérifié sur un
# premier passage réel (gamme CRT), ce texte ne matche jamais aucune nomenclature et noie
# les vrais écarts sous du bruit systématique. Un code Agile ne contient ni espace, ni « + »,
# ni « * » — heuristique volontairement simple plutôt qu'une liste de formats à maintenir.
_JUNK_COMPONENT_RE = re.compile(r"[\s+*]")

# Même jointure que tools/discover_agile.py --bom-of, validée empiriquement sur S128354 :
# BOM.ITEM (numérique) est le parent, résolu via ITEM.ID — pas BOM.ITEM_NUMBER, qui
# identifie la ligne où l'article est utilisé comme composant d'un autre, pas sa propre
# composition (une première version filtrant sur BOM.ITEM_NUMBER ne renvoyait qu'une ligne
# auto-référente). CHANGE_OUT = 0 filtre les lignes actives : les nomenclatures sont
# historisées via ECO, une ligne remplacée reste en base.
BOM_FOR_ITEMS_QUERY = """
    SELECT parent.ITEM_NUMBER AS PARENT_ITEM_NUMBER,
           comp.ITEM_NUMBER AS COMPONENT_ITEM_NUMBER
    FROM BOM b
    JOIN ITEM parent ON parent.ID = b.ITEM
    JOIN ITEM comp ON comp.ID = b.COMPONENT
    WHERE parent.ITEM_NUMBER IN ({item_numbers})
      AND b.CHANGE_OUT = 0
"""


def check_family(family_code: str) -> list[dict]:
    """Vérifie toutes les lignes de grille résolvables d'une gamme contre leur nomenclature
    Agile réelle. Renvoie un écart par (article, option) où le composant attendu n'apparaît
    pas dans la nomenclature active — voir la note sur les variantes en tête de module avant
    de traiter un résultat comme une erreur de grille.
    """
    session = SessionLocal()
    try:
        mappings = (
            session.query(ArticleMapping)
            .filter(ArticleMapping.family_code == family_code, ArticleMapping.item_number.isnot(None))
            .all()
        )
        # Seules les options qui portent un composant Agile connu et propre peuvent être
        # vérifiées ; le reste (non renseigné, ou texte libre non-vérifiable — voir
        # _JUNK_COMPONENT_RE) est hors périmètre, jamais signalé comme une anomalie.
        checkable = [
            (m, o) for m in mappings for o in m.options
            if o.component_item_number and not _JUNK_COMPONENT_RE.search(o.component_item_number)
        ]
        if not checkable:
            return []
        item_numbers = sorted({m.item_number for m, _ in checkable})
    finally:
        session.close()

    conn = connect()
    try:
        quoted = ", ".join(f"'{n}'" for n in item_numbers)
        rows = fetch_all(conn, BOM_FOR_ITEMS_QUERY.format(item_numbers=quoted))
    finally:
        conn.close()

    bom_by_parent: dict[str, set[str]] = {}
    for row in rows:
        bom_by_parent.setdefault(row["PARENT_ITEM_NUMBER"], set()).add(row["COMPONENT_ITEM_NUMBER"])

    discrepancies = []
    for mapping, option in checkable:
        actual = bom_by_parent.get(mapping.item_number, set())
        expected = option.component_item_number
        if expected not in actual:
            discrepancies.append({
                "item_number": mapping.item_number,
                "designation": mapping.designation,
                "option_caption": option.caption,
                "option_label": option.label,
                "expected_component": expected,
                "actual_components": sorted(actual),
            })
    return discrepancies
