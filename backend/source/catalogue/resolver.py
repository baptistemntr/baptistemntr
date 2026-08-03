"""Résolution d'une configuration : options choisies → article, et clé de licence.

C'est l'équivalent des formules du classeur, mais explicite et traçable : la résolution
sait dire *pourquoi* elle a retenu un article.
"""

from sqlalchemy.orm import Session

from catalogue.models import ArticleMapping, LicenseBit, Option, OptionRule


class ConfigurationError(Exception):
    """Combinaison d'options invalide ou sans article correspondant."""


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
            violations.append(rule.message or _default_message(session, rule, "est incompatible avec"))
    return violations


def _default_message(session: Session, rule: OptionRule, verb: str) -> str:
    source = session.get(Option, rule.source_option_id)
    target = session.get(Option, rule.target_option_id)
    return f"« {source.label if source else rule.source_option_id} » {verb} « {target.label if target else rule.target_option_id} »."


def resolve_article(session: Session, family_code: str, selected_ids: set[int]) -> dict:
    """Retourne l'article correspondant à la sélection.

    Un mapping est candidat si toutes ses options sont sélectionnées. Le mapping le plus
    spécifique (celui qui contraint le plus d'options) l'emporte, ce qui reproduit la
    lecture d'une grille de croix où la ligne la plus détaillée prime.
    """
    mappings = (
        session.query(ArticleMapping).filter(ArticleMapping.family_code == family_code).all()
    )
    candidates = [
        m for m in mappings if m.options and {o.id for o in m.options}.issubset(selected_ids)
    ]
    if not candidates:
        raise ConfigurationError(
            "Aucun article ne correspond à cette combinaison d'options."
        )

    best = max(candidates, key=lambda m: len(m.options))
    ties = [m for m in candidates if len(m.options) == len(best.options)]
    if len(ties) > 1:
        raise ConfigurationError(
            "Cette combinaison correspond à plusieurs articles "
            f"({', '.join(m.item_number for m in ties)}) : la grille est ambiguë."
        )

    article = best.article
    return {
        "item_number": best.item_number,
        "designation": best.override_label or (article.description if article else None),
        "commercial_ref": article.commercial_ref if article else None,
        "product_line": article.product_line if article else None,
        # Traçabilité : quelles options ont déclenché ce résultat.
        "matched_on": [{"code": o.code, "label": o.label} for o in best.options],
    }


def build_license(session: Session, family_code: str, selected_ids: set[int]) -> dict:
    """Construit la clé de licence à partir des bits déclarés pour la gamme.

    Le calcul est binaire, comme dans le classeur : chaque bit vaut 1 si son option est
    sélectionnée. L'encodage final (longueur, base, séparateurs, éventuel checksum) reste
    à caler sur l'onglet licence du classeur de référence.
    """
    bits = (
        session.query(LicenseBit)
        .filter(LicenseBit.family_code == family_code)
        .order_by(LicenseBit.position)
        .all()
    )
    if not bits:
        return {}

    values = [1 if (b.option_id is not None and b.option_id in selected_ids) else 0 for b in bits]
    bitstring = "".join(str(v) for v in values)
    return {
        "bits": bitstring,
        "hex": format(int(bitstring, 2), "X").rjust((len(bitstring) + 3) // 4, "0"),
        "detail": [
            {"position": b.position, "label": b.label, "value": v}
            for b, v in zip(bits, values)
        ],
    }
