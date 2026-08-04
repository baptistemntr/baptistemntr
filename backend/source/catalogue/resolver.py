"""Résolution d'une configuration : options choisies → article, prix, clé de licence.

C'est l'équivalent des formules et du VBA du classeur, mais explicite et traçable : la
résolution sait dire *pourquoi* elle a retenu un article, et ce qui manque quand elle n'en
trouve aucun.

La règle de correspondance reproduit `Main_module.Recherche_Code_Article` : la sélection
est comparée à la signature de chaque ligne par **égalité stricte** sur toutes les colonnes
d'options. Une ligne qui exige une option non retenue ne correspond pas ; une ligne qui en
exige moins non plus. C'est volontairement plus sévère qu'une inclusion : le classeur ne
propose jamais un article « approchant », il renvoie « See Manufacturing ».
"""

from sqlalchemy.orm import Session

from catalogue.models import (
    Article, ArticleMapping, LicenseWord, Option, OptionGroup, OptionRule,
)

# Ce que le classeur affiche quand aucune ligne ne correspond.
UNKNOWN_ITEM = "Doesn't exist"
UNKNOWN_DESIGNATION = "See Manufacturing"


def signature_of(captions: list[str] | set[str]) -> str:
    """Signature normalisée d'une combinaison d'options."""
    return "|".join(sorted(captions))


def check_rules(session: Session, family_code: str, selected_ids: set[int]) -> list[str]:
    """Renvoie la liste des violations de compatibilité, vide si la config est valide."""
    violations: list[str] = []
    rules = session.query(OptionRule).filter(OptionRule.family_code == family_code).all()
    for rule in rules:
        if rule.source_option_id not in selected_ids:
            continue
        target_selected = rule.target_option_id in selected_ids
        if rule.kind == "requires" and not target_selected:
            violations.append(rule.message or _default_message(session, rule, "nécessite"))
        elif rule.kind == "excludes" and target_selected:
            violations.append(
                rule.message or _default_message(session, rule, "est incompatible avec")
            )
    return violations


def _default_message(session: Session, rule: OptionRule, verb: str) -> str:
    source = session.get(Option, rule.source_option_id)
    target = session.get(Option, rule.target_option_id)
    return (f"« {source.label if source else rule.source_option_id} » {verb} "
            f"« {target.label if target else rule.target_option_id} ».")


def resolve_article(session: Session, family_code: str, selected_ids: set[int]) -> dict:
    """Retourne l'article correspondant exactement à la sélection.

    Quand aucune ligne ne correspond, on ne lève pas d'erreur : le classeur reste utile
    dans ce cas, en estimant le prix à partir des options retenues. On rend en plus les
    combinaisons voisines, pour que le commercial voie ce qui l'en sépare.
    """
    grid_options = [o for o in _selected_options(session, selected_ids) if o.kind == "grid"]
    selected_captions = {o.caption for o in grid_options}

    mappings = session.query(ArticleMapping).filter(
        ArticleMapping.family_code == family_code
    ).all()
    wanted = signature_of(selected_captions)
    matches = [m for m in mappings if m.signature == wanted]

    if not matches:
        return _no_match(session, family_code, grid_options, mappings, wanted)

    # Deux lignes de même signature : le classeur retient la première et ignore
    # silencieusement les suivantes. On le signale plutôt que de le reproduire.
    best = matches[0]
    article = session.get(Article, best.item_number) if best.item_number else None
    warnings = []
    if len(matches) > 1:
        others = ", ".join(m.item_number or "?" for m in matches[1:])
        warnings.append(
            f"Cette combinaison désigne aussi {others} dans la grille ; "
            f"{best.item_number} est retenu, comme le fait le classeur."
        )

    return {
        "found": True,
        "item_number": best.item_number,
        # Agile fait autorité sur les libellés dès qu'il a été synchronisé ; la valeur du
        # classeur reste le repli, ce qui supprime la ressaisie sans perdre l'existant.
        "designation": (article.description if article else None) or best.designation,
        "commercial_ref": (article.commercial_ref if article else None) or best.commercial_ref,
        "product_line": article.product_line if article else None,
        "price": {"kind": "standard", "amount": best.standard_price}
                 if best.standard_price is not None else _estimate(grid_options),
        "matched_on": [{"caption": o.caption, "label": o.label} for o in grid_options],
        "warnings": warnings,
    }


def _no_match(session: Session, family_code: str, grid_options: list[Option],
              mappings: list[ArticleMapping], wanted: str) -> dict:
    """Réponse quand la combinaison n'existe pas — équivalent de « See Manufacturing »."""
    selected = {o.caption for o in grid_options}
    neighbours = []
    for mapping in mappings:
        existing = set(mapping.signature.split("|")) - {""}
        missing, extra = sorted(existing - selected), sorted(selected - existing)
        neighbours.append((len(missing) + len(extra), mapping, missing, extra))
    neighbours.sort(key=lambda n: n[0])

    return {
        "found": False,
        "item_number": UNKNOWN_ITEM,
        "designation": UNKNOWN_DESIGNATION,
        "commercial_ref": None,
        "product_line": None,
        "price": _estimate(grid_options),
        "matched_on": [{"caption": o.caption, "label": o.label} for o in grid_options],
        "warnings": ["Aucun article ne correspond exactement à cette combinaison."],
        # De quoi expliquer l'échec sans avoir à ouvrir la grille.
        "closest": [{
            "item_number": mapping.item_number,
            "designation": mapping.designation,
            "missing": missing,
            "extra": extra,
        } for _, mapping, missing, extra in neighbours[:3]],
    }


def _estimate(grid_options: list[Option]) -> dict:
    """Estime le prix en sommant celui des options, comme `Recherche_prix` du classeur.

    Le classeur refuse d'estimer dès qu'une option retenue n'a pas de prix ; on conserve
    ce comportement mais on dit lesquelles manquent, pour que l'IMI puisse compléter.
    """
    missing = [o.label for o in grid_options if o.unit_price is None]
    if missing:
        return {"kind": "unavailable", "amount": None, "missing_prices": missing}
    return {"kind": "estimate", "amount": sum(o.unit_price for o in grid_options)}


def _selected_options(session: Session, selected_ids: set[int]) -> list[Option]:
    if not selected_ids:
        return []
    return session.query(Option).filter(Option.id.in_(selected_ids)).all()


# --- CRT (FEP) -----------------------------------------------------------------------
#
# Contrairement à HDR, l'onglet « Licence FEP » ne calcule aucun mot en somme pondérée :
# la section « 9 - Dongle FEP » du classeur (`CRT!B49:J61`) affiche telle quelle une table
# de fonctions actives (identifiant + libellé + booléen) et cinq compteurs matériels
# encodés en hexadécimal sur deux chiffres, à charge pour l'IMI de les reporter à la main
# dans l'outil de programmation du dongle. `build_fep_license` reproduit cette table.
#
# Chaque fonction référence le(s) contrôle(s) CRT dont dépend son booléen dans
# `Licence FEP` (OR s'il y en a plusieurs, comme pour HDR) ; certaines sont de purs
# miroirs d'un autre contrôle (`C7=C5`, `C9=C11`, `C14=C10`) ou de la même case combinée
# (`C23=OR(C11,C12)`, utilisée telle quelle par les DEUX lignes 22 et 24 du classeur — un
# raccourci d'affichage du classeur, reproduit à l'identique, pas une erreur de reprise).
FEP_FUNCTIONS: list[tuple[int, str, list[str]]] = [
    (1, "RDP access", ["CheckBox4"]),
    (2, "COP-1", ["CheckBox16"]),
    (20, "FEP Product", ["CheckBox4"]),
    (21, "FEP - TC Segment", ["CheckBox17"]),
    (22, "FEP - TC Encrypt", ["CheckBox19", "CheckBox20"]),
    (23, "FEP - TM packet", ["CheckBox13"]),
    (24, "FEP - TM Decrypt", ["CheckBox19", "CheckBox20"]),
    (25, "FEP - HSM option", ["CheckBox20"]),
    (26, "FEP - TC Spacebus", []),
    (27, "FEP - AOS Protocol", ["CheckBox13"]),
    (28, "FEP - Dual Packet", ["CheckBox14"]),
]

# code, libellé, quantité max (`K3:K7`), contrôle(s) qui l'activent (`L3:L7`).
FEP_COUNTERS: list[tuple[str, str, int, list[str]]] = [
    ("TPP", "Telecommand Packet Processor Unit mounted", 6,
     ["CheckBox16", "CheckBox17", "CheckBox15"]),
    ("SPP", "TM Space Packet Processor Unit mounted", 6,
     ["CheckBox13", "CheckBox14", "CheckBox19", "CheckBox20", "CheckBox15"]),
    ("IFS", "Internal Frame Synchronization mounted", 6, ["CheckBox14"]),
    ("UTP", "Uplink Telemetry Processor Unit mounted", 2, ["CheckBox15"]),
    ("ECP", "Echo Commanding Processor Unit mounted", 2, ["CheckBox18"]),
]

DONGLE_WITH_ENCRYPTION = "S157786"
DONGLE_WITHOUT_ENCRYPTION = "S157787"


def build_fep_license(session: Session, selected_ids: set[int]) -> dict:
    """Table de licence CRT (dongle FEP) — voir `FEP_FUNCTIONS` ci-dessus."""
    options = (
        session.query(Option).join(OptionGroup)
        .filter(OptionGroup.family_code == "CRT", Option.kind == "license")
        .all()
    )
    selected_controls = {o.control_name for o in options if o.id in selected_ids}

    def any_on(controls: list[str]) -> bool:
        return any(c in selected_controls for c in controls)

    functions = [
        {
            "id": function_id,
            "label": label,
            "active": any_on(controls),
            "unmapped_reason": None if controls else (
                "Aucun contrôle de l'écran CRT ne pilote cette fonction — "
                "Licence FEP!C13 reste figé à FAUX dans le classeur."
            ),
        }
        for function_id, label, controls in FEP_FUNCTIONS
    ]
    counters = [
        {
            "code": code,
            "label": label,
            "count": max_count if any_on(controls) else 0,
            # `DEC2HEX(BIN2DEC(REPT("0",6-L)&REPT("1",L)),2)` : les `L` bits bas à 1, pas
            # la valeur `L` elle-même — 6 unités s'écrit 0x3F (0b111111), pas 0x06.
            "hex": format((1 << max_count) - 1 if any_on(controls) else 0, "02X"),
        }
        for code, label, max_count, controls in FEP_COUNTERS
    ]

    rdp_access = any_on(["CheckBox4"])
    encryption = any_on(["CheckBox19", "CheckBox20"])
    dongle_part_number = (
        "NA" if not rdp_access
        else DONGLE_WITH_ENCRYPTION if encryption else DONGLE_WITHOUT_ENCRYPTION
    )

    return {
        "kind": "fep",
        "dongle_part_number": dongle_part_number,
        "functions": functions,
        "counters": counters,
    }


def build_license(session: Session, family_code: str, selected_ids: set[int]) -> dict:
    """Construit la licence de la gamme.

    CRT suit un schéma dédié (`build_fep_license`, table de fonctions + compteurs). Les
    autres gammes à licence (HDR pour l'instant) sont des mots en somme pondérée : un bit
    retenu ajoute son poids, et le total est rendu en hexadécimal — transposition directe
    de `DEC2HEX(SUMIF(valeurs; VRAI; poids))` de l'onglet « Licences <Gamme> ».
    """
    if family_code == "CRT":
        return build_fep_license(session, selected_ids)

    words = (
        session.query(LicenseWord)
        .filter(LicenseWord.family_code == family_code)
        .order_by(LicenseWord.position)
        .all()
    )
    if not words:
        return {}

    out = {}
    for word in words:
        total = 0
        detail = []
        for bit in word.bits:
            # OR : un bit peut dépendre de plusieurs options (ex. « 4D-TCM ou 6D-TCM »).
            on = any(o.id in selected_ids for o in bit.options)
            total += bit.weight if on else 0
            detail.append({
                "position": bit.position, "weight": bit.weight, "label": bit.label,
                "value": int(on), "unmapped_reason": bit.unmapped_reason,
            })
        out[word.code] = {
            "label": word.label,
            "value": total,
            "hex": format(total, "X"),
            "bits": "".join(str(d["value"]) for d in reversed(detail)),
            "detail": detail,
        }
    return out
