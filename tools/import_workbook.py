#!/usr/bin/env python3
"""Traduit le classeur Excel en données exploitables par le catalogue.

Le classeur suit une convention stricte, découverte par rétro-ingénierie du VBA
(`Main_module.Recherche_Code_Article`) et vérifiée sur les 21 gammes. Pour chaque
onglet « Base de données <Gamme> » :

    ligne 2   commentaire technique de l'option  (matière des infobulles)
    ligne 3   code article du composant apporté par l'option
    ligne 4   prix standard de l'option          (sert à l'estimation)
    ligne 5   en-têtes : A=Produit, B=Désignation, C=Référence commerciale,
              puis une colonne par option à partir de D, jusqu'à la colonne « PRS »
    ligne 6+  un article par ligne ; une croix marque les options qu'il embarque,
              la colonne « PRS » porte son prix standard

L'en-tête d'une colonne d'option est le *Caption* d'un contrôle ActiveX de l'onglet de
gamme : c'est cette égalité de texte qui relie l'écran à la grille (cf.
`tools/extract_controls.py`).

    python3 tools/import_workbook.py "data/Catalogue industriel.xlsm" \
        --sortie data/catalogue.json --rapport docs/05-diagnostic-classeur.md
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from openpyxl import load_workbook
except ImportError:
    sys.exit("openpyxl requis : pip install openpyxl")

sys.path.insert(0, str(Path(__file__).parent))
from extract_controls import extract  # noqa: E402

DB_PREFIX = "Base de données "
ROW_COMMENT, ROW_COMPONENT, ROW_PRICE, ROW_HEADER = 2, 3, 4, 5
FIRST_ARTICLE_ROW = 6
COL_ITEM, COL_DESIGNATION, COL_COMMERCIAL_REF, FIRST_OPTION_COL = 1, 2, 3, 4
END_MARKER = "PRS"

# Colonnes créées par Excel lors de la mise en tableau, sans signification métier.
JUNK_HEADERS = {"colonne1", "colonne2", "colonne3"}

# Drapeau « aucune demande spécifique », présent sur chaque écran ; il déclenche un
# avertissement à l'export (`Buttons_module.Specific_request_warning`) et ne configure rien.
SPECIFIC_REQUEST_CONTROL = "Specific_request_checkbox"


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _price(value) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def read_family(ws, controls: list[dict]) -> dict:
    """Lit un onglet « Base de données » et le recoud avec les contrôles de l'écran."""
    by_caption = {c["caption"].strip(): c for c in controls if c.get("caption")}

    options: list[dict] = []
    col = FIRST_OPTION_COL
    while True:
        header = _text(ws.cell(ROW_HEADER, col).value)
        if header is None or header == END_MARKER:
            break
        control = by_caption.get(header)
        options.append({
            "column": col,
            "caption": header,
            "section": _text(ws.cell(1, col).value),
            "comment": _text(ws.cell(ROW_COMMENT, col).value),
            "component_item_number": _text(ws.cell(ROW_COMPONENT, col).value),
            "unit_price": _price(ws.cell(ROW_PRICE, col).value),
            "control_name": control["name"] if control else None,
            "control_type": control.get("type") if control else None,
            "group": (control.get("group") or None) if control else None,
            "linked_cell": control.get("linked_cell") if control else None,
        })
        col += 1
    price_col = col  # la colonne « PRS »

    articles: list[dict] = []
    row = FIRST_ARTICLE_ROW
    while _text(ws.cell(row, COL_DESIGNATION).value):
        selected = [o["caption"] for o in options
                    if _text(ws.cell(row, o["column"]).value) is not None]
        articles.append({
            "row": row,
            "item_number": _text(ws.cell(row, COL_ITEM).value),
            "designation": _text(ws.cell(row, COL_DESIGNATION).value),
            "commercial_ref": _text(ws.cell(row, COL_COMMERCIAL_REF).value),
            "standard_price": _price(ws.cell(row, price_col).value),
            "options": selected,
        })
        row += 1

    # Tous les autres contrôles de l'écran : options de licence, choix neutres « None »
    # des groupes exclusifs, attributs commerciaux (durée, mode de livraison). Ils
    # n'entrent pas dans le calcul de l'article mais font partie de la configuration —
    # la contrainte de non-régression impose de les conserver.
    in_grid = {o["caption"] for o in options}
    extra_options = [{
        "caption": control["caption"].strip(),
        "control_name": control["name"],
        "control_type": control.get("type"),
        "group": control.get("group") or None,
        "linked_cell": control.get("linked_cell"),
        "role": "licence" if control.get("linked_cell") else "commercial",
    } for control in controls
        if control.get("caption")
        and control["caption"].strip() not in in_grid
        and control["name"] != SPECIFIC_REQUEST_CONTROL]

    return {"options": options, "articles": articles, "extra_options": extra_options}


def build_groups(options: list[dict]) -> list[dict]:
    """Reconstitue les questions posées au commercial.

    Un `GroupName` partagé entre boutons radio est un choix exclusif ; chaque case à
    cocher est une question binaire indépendante. Les colonnes sans contrôle ne sont
    rattachées à aucun groupe : elles sont signalées par le diagnostic.
    """
    groups: dict[str, dict] = {}
    for option in options:
        if option["control_type"] == "OptionButton" and option["group"]:
            key, selection = f"grp:{option['group']}", "single"
        else:
            key, selection = f"opt:{option['caption']}", "boolean"
        group = groups.setdefault(key, {
            "code": option["group"] if selection == "single" else option["caption"],
            "label": option["group"] if selection == "single" else option["caption"],
            "selection": selection,
            "section": option["section"],
            "options": [],
        })
        group["options"].append(option["caption"])
    return list(groups.values())


def diagnose(code: str, family: dict, controls: list[dict]) -> list[dict]:
    """Repère ce qui, dans le classeur, ne peut pas fonctionner tel quel.

    Ces anomalies sont à trancher avec l'IMI : elles ne sont pas corrigées d'office,
    la contrainte de non-régression interdisant de décider seul.
    """
    findings: list[dict] = []
    options = family["options"]

    for option in options:
        if option["caption"].lower() in JUNK_HEADERS:
            findings.append({"gamme": code, "type": "colonne-technique",
                             "detail": f"colonne « {option['caption']} » "
                                       "(artefact de mise en tableau Excel, sans option associée)"})
        elif option["control_name"] is None:
            findings.append({"gamme": code, "type": "colonne-sans-controle",
                             "detail": f"« {option['caption']} » : aucun contrôle de l'écran "
                                       "ne porte ce libellé, la colonne ne peut jamais être cochée"})

    for control in controls:
        if not (control.get("caption") or "").strip():
            findings.append({"gamme": code, "type": "controle-sans-libelle",
                             "detail": f"contrôle « {control['name']} » sans Caption : il ne peut "
                                       "correspondre à aucune colonne de la grille"})

    # Un article dont une option n'est jamais cochable est inatteignable : la
    # comparaison du VBA est une égalité stricte sur toutes les colonnes.
    unreachable = {o["caption"] for o in options if o["control_name"] is None}
    signatures: dict[tuple, dict] = {}
    for article in family["articles"]:
        blocking = sorted(set(article["options"]) & unreachable)
        if blocking:
            findings.append({"gamme": code, "type": "article-inatteignable",
                             "detail": f"{article['item_number']} (ligne {article['row']}) exige "
                                       f"{', '.join(blocking)}, jamais sélectionnable"})
        signature = tuple(sorted(article["options"]))
        if signature in signatures:
            first = signatures[signature]
            findings.append({"gamme": code, "type": "signature-dupliquee",
                             "detail": f"{article['item_number']} (ligne {article['row']}) a la même "
                                       f"combinaison que {first['item_number']} (ligne {first['row']}) : "
                                       "seul le premier peut être retourné"})
        else:
            signatures[signature] = article
        if not article["options"]:
            findings.append({"gamme": code, "type": "article-sans-option",
                             "detail": f"{article['item_number']} (ligne {article['row']}) ne coche "
                                       "aucune option : il ne sort que sur une configuration vide"})

    return findings


def write_report(path: Path, catalogue: dict) -> None:
    lines = ["# Diagnostic du classeur\n",
             "> Produit par `tools/import_workbook.py`. Ce document liste ce que la reprise du\n"
             "> classeur ne peut pas trancher seule : chaque point est à valider avec l'IMI avant\n"
             "> la bascule, la contrainte de non-régression interdisant toute correction d'office.\n"]

    lines.append("\n## Volumétrie\n")
    lines.append("| Gamme | Options de grille | Autres options | Articles | Licence | Anomalies |")
    lines.append("|-------|------------------:|---------------:|---------:|:-------:|----------:|")
    for family in catalogue["families"]:
        lines.append(f"| {family['code']} | {len(family['options'])} | "
                     f"{len(family['extra_options'])} | {len(family['articles'])} "
                     f"| {'oui' if family['has_license'] else '—'} | {len(family['findings'])} |")

    by_type: dict[str, list[dict]] = {}
    for family in catalogue["families"]:
        for finding in family["findings"]:
            by_type.setdefault(finding["type"], []).append(finding)

    titles = {
        "colonne-technique": "Colonnes techniques résiduelles",
        "colonne-sans-controle": "Colonnes que l'écran ne peut pas cocher",
        "controle-sans-libelle": "Contrôles sans libellé",
        "article-inatteignable": "Articles inatteignables",
        "signature-dupliquee": "Combinaisons en double",
        "article-sans-option": "Articles sans aucune option",
    }
    for kind, findings in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"\n## {titles.get(kind, kind)} ({len(findings)})\n")
        for finding in findings:
            lines.append(f"- **{finding['gamme']}** — {finding['detail']}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--sortie", type=Path, default=Path("data/catalogue.json"))
    parser.add_argument("--rapport", type=Path)
    args = parser.parse_args()

    controls_by_sheet = extract(args.workbook)
    wb = load_workbook(args.workbook, data_only=True)

    families = []
    for sheet in wb.sheetnames:
        if not sheet.startswith(DB_PREFIX):
            continue
        code = sheet[len(DB_PREFIX):]
        if code not in wb.sheetnames:
            continue  # onglet d'archive, sans écran de configuration
        controls = controls_by_sheet.get(code, [])
        family = read_family(wb[sheet], controls)
        family.update({
            "code": code,
            "label": code,
            # Une gamme porte des licences dès qu'un de ses contrôles alimente un onglet
            # « Licence… ». Le nom de cet onglet ne suit pas la gamme : CRT alimente
            # « Licence FEP », HDR « Licences HDR ».
            "has_license": any(o["linked_cell"] and o["linked_cell"].lstrip("'").startswith("Licence")
                               for o in family["extra_options"]),
            "groups": build_groups(family["options"]),
            "findings": diagnose(code, family, controls),
        })
        families.append(family)

    catalogue = {"source": args.workbook.name, "families": families}
    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    args.sortie.write_text(json.dumps(catalogue, ensure_ascii=False, indent=1), encoding="utf-8")

    total = sum(len(f["findings"]) for f in families)
    print(f"{len(families)} gammes, "
          f"{sum(len(f['options']) for f in families)} options, "
          f"{sum(len(f['articles']) for f in families)} articles, "
          f"{total} anomalies → {args.sortie}", file=sys.stderr)

    if args.rapport:
        write_report(args.rapport, catalogue)
        print(f"rapport → {args.rapport}", file=sys.stderr)


if __name__ == "__main__":
    main()
