"""Chargement du catalogue produit par `tools/import_workbook.py`.

La reprise est **idempotente et non destructive pour Agile** : elle remplace la
configuration tenue par l'IMI (gammes, options, grille) et ne touche jamais à la table
`article`, qui n'appartient qu'à la synchro Snowflake.
"""

import json
from pathlib import Path

from sqlalchemy.orm import Session

from catalogue.models import (
    ArticleMapping, Option, OptionGroup, ProductFamily,
)
from catalogue.resolver import signature_of


def load_catalogue(session: Session, path: Path) -> dict:
    """Remplace la configuration par celle du fichier, et rend un compte rendu."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    report = {"families": 0, "options": 0, "articles": 0, "findings": 0}
    for position, family in enumerate(data["families"]):
        _replace_family(session, family, position)
        report["families"] += 1
        report["options"] += len(family["options"]) + len(family["extra_options"])
        report["articles"] += len(family["articles"])
        report["findings"] += len(family["findings"])

    session.commit()
    return report


def _replace_family(session: Session, family: dict, position: int) -> None:
    code = family["code"]

    # L'ordre compte : la grille référence les options, les options les groupes.
    session.query(ArticleMapping).filter(ArticleMapping.family_code == code).delete()
    for group in session.query(OptionGroup).filter(OptionGroup.family_code == code).all():
        session.delete(group)
    session.flush()

    record = session.get(ProductFamily, code) or ProductFamily(code=code)
    record.label = family["label"]
    record.has_license = family["has_license"]
    record.position = position
    session.add(record)
    session.flush()

    options_by_caption: dict[str, Option] = {}
    for index, group in enumerate(family["groups"]):
        options_by_caption.update(
            _add_group(session, code, group, index, family["options"], kind="grid")
        )

    # Options hors grille : elles ne changent pas l'article mais restent au récapitulatif.
    extras = family["extra_options"]
    if extras:
        options_by_caption.update(_add_extra_options(session, code, extras, len(family["groups"])))

    for article in family["articles"]:
        session.add(ArticleMapping(
            family_code=code,
            item_number=article["item_number"],
            designation=article["designation"],
            commercial_ref=article["commercial_ref"],
            standard_price=article["standard_price"],
            signature=signature_of(article["options"]),
            source_row=article["row"],
            options=[options_by_caption[c] for c in article["options"]
                     if c in options_by_caption],
        ))


def _add_group(session: Session, family_code: str, group: dict, position: int,
               options: list[dict], kind: str) -> dict[str, Option]:
    detail = {o["caption"]: o for o in options}
    record = OptionGroup(
        family_code=family_code,
        code=group["code"],
        label=group["label"],
        section=group["section"],
        selection=group["selection"],
        position=position,
    )
    session.add(record)
    session.flush()

    created = {}
    for index, caption in enumerate(group["options"]):
        source = detail.get(caption, {})
        option = Option(
            group_id=record.id,
            caption=caption,
            # Le libellé commercial reste à écrire avec l'IMI ; en attendant, le libellé
            # du classeur fait foi, ce qui évite d'inventer du vocabulaire.
            label=caption,
            technical_label=source.get("comment"),
            kind=kind,
            component_item_number=source.get("component_item_number"),
            unit_price=source.get("unit_price"),
            source_column=source.get("column"),
            control_name=source.get("control_name"),
            position=index,
        )
        session.add(option)
        created[caption] = option
    session.flush()
    return created


def _add_extra_options(session: Session, family_code: str, extras: list[dict],
                       position: int) -> dict[str, Option]:
    """Regroupe les options hors grille par rôle (licence, commercial)."""
    created: dict[str, Option] = {}
    for offset, role in enumerate(("licence", "commercial")):
        selection = [e for e in extras if e["role"] == role]
        if not selection:
            continue
        group = OptionGroup(
            family_code=family_code,
            code=f"__{role}",
            label="Licences" if role == "licence" else "Options commerciales",
            selection="boolean",
            position=position + offset,
        )
        session.add(group)
        session.flush()
        for index, extra in enumerate(selection):
            option = Option(
                group_id=group.id,
                # Hors grille, plusieurs contrôles partagent parfois le même libellé
                # (« Specific », « FIR »…) : c'est le nom du contrôle qui les distingue.
                caption=extra["control_name"],
                label=extra["caption"],
                kind="license" if role == "licence" else "commercial",
                control_name=extra["control_name"],
                position=index,
            )
            session.add(option)
            created.setdefault(extra["caption"], option)
        session.flush()
    return created
