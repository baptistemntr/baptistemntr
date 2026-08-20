"""Espace IMI : édition directe du référentiel (gammes, groupes, options, grille, règles).

Remplace, pour ce qui est couvert, le passage obligé par `tools/import_workbook.py` et le
classeur Excel — c'est tout l'objet de cet écran (voir docs/02-architecture.md § 2).
Toutes les gammes sont éditables (voir docs/06-admin-imi.md), avec deux limites :

- pas de création de nouvelle gamme ;
- `Option.caption` et `OptionGroup.code` ne se fixent qu'à la création : ce sont les clés
  stables dont dépend la résolution (`resolver.signature_of`), les renommer casserait
  silencieusement la grille — voir `docs/04-regles-du-classeur.md` § 3.

Les mots/bits de licence (HDR, SATCORE) sont éditables ici aussi — même modèle en somme
pondérée que le reste (`resolver.build_license`). CRT (FEP) ne l'est pas : sa licence est
codée en dur dans `resolver.build_fep_license`, pas en base — créer un mot de licence pour
CRT ici n'aurait aucun effet (le dispatch vers `build_fep_license` court-circuite toute
lecture de `LicenseWord`), donc c'est refusé explicitement plutôt que de laisser une
entrée fantôme.

Protégé par un mot de passe partagé (`ADMIN_PASSWORD`, en-tête `X-Admin-Password`) : c'est
un espace d'écriture sur ce que voient les commerciaux, pas la configuration en lecture
seule.
"""

import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from catalogue import bom_check, snowflake_client
from catalogue.database import SessionLocal
from catalogue.models import (
    ArticleMapping, LicenseBit, LicenseWord, Option, OptionGroup, OptionRule, ProductFamily,
)
from catalogue.resolver import signature_of
from catalogue.schemas import (
    AdminArticleCreate,
    AdminArticleOut,
    AdminArticleUpdate,
    AdminFamilyDetailOut,
    AdminFamilyUpdate,
    AdminGroupCreate,
    AdminGroupOut,
    AdminGroupUpdate,
    AdminLicenseBitCreate,
    AdminLicenseBitOut,
    AdminLicenseBitUpdate,
    AdminLicenseWordCreate,
    AdminLicenseWordOut,
    AdminLicenseWordUpdate,
    AdminOptionCreate,
    AdminOptionOut,
    AdminOptionUpdate,
    AdminRuleCreate,
    AdminRuleOut,
    BomDiscrepancyOut,
    FamilyOut,
)

# CRT (FEP) court-circuite LicenseWord — voir resolver.build_license. Un mot créé pour
# cette gamme ne serait jamais lu, donc jamais consulté ni utilisé : mieux vaut le refuser
# explicitement que laisser une entrée fantôme dans la base.
_NO_LICENSE_WORDS_FAMILY = "CRT"

def require_admin(x_admin_password: str | None = Header(default=None)) -> None:
    # Un en-tête maison plutôt que `Authorization: Basic` : ce dernier fait entrer en jeu
    # la gestion native des identifiants du navigateur (cache par origine, ré-essai
    # automatique) dès qu'un 401 survient, ce qui entre en conflit avec le formulaire de
    # connexion JS — reproduit concrètement (un mauvais mot de passe suivi du bon reste
    # bloqué). Un en-tête que le navigateur ne reconnaît pas évite tout ça.
    expected = os.getenv("ADMIN_PASSWORD")
    if not expected:
        # Un espace d'écriture sans mot de passe configuré doit rester fermé, pas ouvert
        # par défaut : une variable d'environnement oubliée ne doit jamais se traduire par
        # un accès libre.
        raise HTTPException(status_code=503, detail="ADMIN_PASSWORD n'est pas configuré.")
    # compare_digest : évite qu'une attaque par mesure de temps ne devine le mot de passe
    # caractère par caractère.
    if not x_admin_password or not secrets.compare_digest(x_admin_password, expected):
        raise HTTPException(status_code=401, detail="Mot de passe incorrect.")


router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _session() -> Session:
    return SessionLocal()


def _get_family(session: Session, code: str) -> ProductFamily:
    family = session.get(ProductFamily, code)
    if family is None:
        raise HTTPException(status_code=404, detail=f"Gamme inconnue : {code}")
    return family


def _get_group(session: Session, group_id: int) -> OptionGroup:
    group = session.get(OptionGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail=f"Groupe inconnu : {group_id}")
    return group


def _get_option(session: Session, option_id: int) -> Option:
    option = session.get(Option, option_id)
    if option is None:
        raise HTTPException(status_code=404, detail=f"Option inconnue : {option_id}")
    return option


def _grid_options(session: Session, family_code: str, option_ids: list[int]) -> list[Option]:
    """Résout des ids en options `grid` de la gamme — celles qui forment la signature."""
    if not option_ids:
        return []
    options = (
        session.query(Option).join(OptionGroup)
        .filter(Option.id.in_(option_ids), OptionGroup.family_code == family_code)
        .all()
    )
    found_ids = {o.id for o in options}
    missing = set(option_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Option(s) inconnue(s) pour la gamme {family_code} : {sorted(missing)}",
        )
    not_grid = [o.caption for o in options if o.kind != "grid"]
    if not_grid:
        raise HTTPException(
            status_code=422,
            detail=f"Ces options ne participent pas à la grille (kind ≠ grid) : {not_grid}",
        )
    return options


def _article_out(mapping: ArticleMapping) -> AdminArticleOut:
    return AdminArticleOut(
        id=mapping.id, family_code=mapping.family_code, item_number=mapping.item_number,
        designation=mapping.designation, commercial_ref=mapping.commercial_ref,
        standard_price=mapping.standard_price,
        option_ids=[o.id for o in mapping.options],
        captions=sorted(o.caption for o in mapping.options),
    )


def _get_word(session: Session, word_id: int) -> LicenseWord:
    word = session.get(LicenseWord, word_id)
    if word is None:
        raise HTTPException(status_code=404, detail=f"Mot de licence inconnu : {word_id}")
    return word


def _get_bit(session: Session, bit_id: int) -> LicenseBit:
    bit = session.get(LicenseBit, bit_id)
    if bit is None:
        raise HTTPException(status_code=404, detail=f"Bit de licence inconnu : {bit_id}")
    return bit


def _license_options(session: Session, family_code: str, option_ids: list[int]) -> list[Option]:
    """Résout des ids en options `license` de la gamme — celles qu'un bit peut référencer."""
    if not option_ids:
        return []
    options = (
        session.query(Option).join(OptionGroup)
        .filter(Option.id.in_(option_ids), OptionGroup.family_code == family_code)
        .all()
    )
    found_ids = {o.id for o in options}
    missing = set(option_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Option(s) inconnue(s) pour la gamme {family_code} : {sorted(missing)}",
        )
    not_license = [o.caption for o in options if o.kind != "license"]
    if not_license:
        raise HTTPException(
            status_code=422,
            detail=f"Ces options ne sont pas des options de licence (kind ≠ license) : {not_license}",
        )
    return options


def _bit_out(bit: LicenseBit) -> AdminLicenseBitOut:
    return AdminLicenseBitOut(
        id=bit.id, word_id=bit.word_id, position=bit.position, weight=bit.weight,
        label=bit.label, source_cell=bit.source_cell, unmapped_reason=bit.unmapped_reason,
        constant_value=bit.constant_value, option_ids=[o.id for o in bit.options],
    )


def _word_out(word: LicenseWord) -> AdminLicenseWordOut:
    return AdminLicenseWordOut(
        id=word.id, family_code=word.family_code, code=word.code, label=word.label,
        position=word.position, bits=[_bit_out(b) for b in word.bits],
    )


@router.get("/families", response_model=list[FamilyOut])
def list_families() -> list[FamilyOut]:
    """Sert le sélecteur de gamme de l'espace admin — et vérifie le mot de passe au passage
    (le login n'a pas d'endpoint dédié : c'est le premier appel authentifié qui fait foi).
    """
    session = _session()
    try:
        families = session.query(ProductFamily).order_by(ProductFamily.position).all()
        return [FamilyOut.model_validate(f, from_attributes=True) for f in families]
    finally:
        session.close()


@router.get("/families/{code}", response_model=AdminFamilyDetailOut)
def get_family(code: str) -> AdminFamilyDetailOut:
    session = _session()
    try:
        family = _get_family(session, code)
        articles = (
            session.query(ArticleMapping).filter(ArticleMapping.family_code == code).all()
        )
        rules = session.query(OptionRule).filter(OptionRule.family_code == code).all()
        words = (
            session.query(LicenseWord).filter(LicenseWord.family_code == code)
            .order_by(LicenseWord.position).all()
        )
        return AdminFamilyDetailOut(
            code=family.code, label=family.label, description=family.description,
            has_license=family.has_license,
            groups=[AdminGroupOut.model_validate(g, from_attributes=True) for g in family.groups],
            articles=[_article_out(a) for a in articles],
            rules=[AdminRuleOut.model_validate(r, from_attributes=True) for r in rules],
            license_words=[_word_out(w) for w in words],
        )
    finally:
        session.close()


@router.get("/families/{code}/bom-check", response_model=list[BomDiscrepancyOut])
def check_family_bom(code: str) -> list[BomDiscrepancyOut]:
    """Compare la grille de la gamme à la nomenclature Agile réelle — voir bom_check.py.

    Appelle Snowflake en direct à chaque appel (pas de miroir local pour le BOM,
    contrairement aux articles) : un résultat vide peut vouloir dire soit « rien à
    signaler », soit « aucune option de cette gamme ne porte de component_item_number »
    (aujourd'hui la majorité) — les deux se distinguent par le contenu du rapport, jamais
    par une alerte silencieuse.
    """
    session = _session()
    try:
        _get_family(session, code)  # 404 propre si la gamme n'existe pas
    finally:
        session.close()
    if not snowflake_client.is_configured():
        raise HTTPException(
            status_code=503, detail="Identifiants Snowflake absents de l'environnement."
        )
    return [BomDiscrepancyOut(**d) for d in bom_check.check_family(code)]


@router.put("/families/{code}", response_model=AdminFamilyDetailOut)
def update_family(code: str, payload: AdminFamilyUpdate) -> AdminFamilyDetailOut:
    session = _session()
    try:
        family = _get_family(session, code)
        family.label = payload.label
        family.description = payload.description
        session.commit()
    finally:
        session.close()
    return get_family(code)


@router.post("/groups", response_model=AdminGroupOut)
def create_group(payload: AdminGroupCreate) -> AdminGroupOut:
    session = _session()
    try:
        _get_family(session, payload.family_code)
        group = OptionGroup(**payload.model_dump())
        session.add(group)
        session.commit()
        session.refresh(group)
        return AdminGroupOut.model_validate(group, from_attributes=True)
    finally:
        session.close()


@router.put("/groups/{group_id}", response_model=AdminGroupOut)
def update_group(group_id: int, payload: AdminGroupUpdate) -> AdminGroupOut:
    session = _session()
    try:
        group = _get_group(session, group_id)
        for field, value in payload.model_dump().items():
            setattr(group, field, value)
        session.commit()
        session.refresh(group)
        return AdminGroupOut.model_validate(group, from_attributes=True)
    finally:
        session.close()


@router.delete("/groups/{group_id}", status_code=204)
def delete_group(group_id: int) -> None:
    session = _session()
    try:
        group = _get_group(session, group_id)
        session.delete(group)
        session.commit()
    finally:
        session.close()


@router.post("/options", response_model=AdminOptionOut)
def create_option(payload: AdminOptionCreate) -> AdminOptionOut:
    session = _session()
    try:
        _get_group(session, payload.group_id)
        option = Option(**payload.model_dump())
        session.add(option)
        session.commit()
        session.refresh(option)
        return AdminOptionOut.model_validate(option, from_attributes=True)
    finally:
        session.close()


@router.put("/options/{option_id}", response_model=AdminOptionOut)
def update_option(option_id: int, payload: AdminOptionUpdate) -> AdminOptionOut:
    session = _session()
    try:
        option = _get_option(session, option_id)
        for field, value in payload.model_dump().items():
            setattr(option, field, value)
        session.commit()
        session.refresh(option)
        return AdminOptionOut.model_validate(option, from_attributes=True)
    finally:
        session.close()


@router.delete("/options/{option_id}", status_code=204)
def delete_option(option_id: int) -> None:
    session = _session()
    try:
        option = _get_option(session, option_id)
        session.delete(option)
        session.commit()
    finally:
        session.close()


@router.post("/articles", response_model=AdminArticleOut)
def create_article(payload: AdminArticleCreate) -> AdminArticleOut:
    session = _session()
    try:
        _get_family(session, payload.family_code)
        options = _grid_options(session, payload.family_code, payload.option_ids)
        mapping = ArticleMapping(
            family_code=payload.family_code, item_number=payload.item_number,
            designation=payload.designation, commercial_ref=payload.commercial_ref,
            standard_price=payload.standard_price,
            signature=signature_of([o.caption for o in options]),
            options=options,
        )
        session.add(mapping)
        session.commit()
        session.refresh(mapping)
        return _article_out(mapping)
    finally:
        session.close()


@router.put("/articles/{article_id}", response_model=AdminArticleOut)
def update_article(article_id: int, payload: AdminArticleUpdate) -> AdminArticleOut:
    session = _session()
    try:
        mapping = session.get(ArticleMapping, article_id)
        if mapping is None:
            raise HTTPException(status_code=404, detail=f"Ligne de grille inconnue : {article_id}")
        options = _grid_options(session, mapping.family_code, payload.option_ids)
        mapping.item_number = payload.item_number
        mapping.designation = payload.designation
        mapping.commercial_ref = payload.commercial_ref
        mapping.standard_price = payload.standard_price
        mapping.options = options
        mapping.signature = signature_of([o.caption for o in options])
        session.commit()
        session.refresh(mapping)
        return _article_out(mapping)
    finally:
        session.close()


@router.delete("/articles/{article_id}", status_code=204)
def delete_article(article_id: int) -> None:
    session = _session()
    try:
        mapping = session.get(ArticleMapping, article_id)
        if mapping is None:
            raise HTTPException(status_code=404, detail=f"Ligne de grille inconnue : {article_id}")
        session.delete(mapping)
        session.commit()
    finally:
        session.close()


@router.post("/rules", response_model=AdminRuleOut)
def create_rule(payload: AdminRuleCreate) -> AdminRuleOut:
    session = _session()
    try:
        _get_family(session, payload.family_code)
        if payload.kind not in ("requires", "excludes"):
            raise HTTPException(status_code=422, detail="kind doit être requires ou excludes.")
        _get_option(session, payload.source_option_id)
        _get_option(session, payload.target_option_id)
        rule = OptionRule(**payload.model_dump())
        session.add(rule)
        session.commit()
        session.refresh(rule)
        return AdminRuleOut.model_validate(rule, from_attributes=True)
    finally:
        session.close()


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int) -> None:
    session = _session()
    try:
        rule = session.get(OptionRule, rule_id)
        if rule is None:
            raise HTTPException(status_code=404, detail=f"Règle inconnue : {rule_id}")
        session.delete(rule)
        session.commit()
    finally:
        session.close()


@router.post("/license-words", response_model=AdminLicenseWordOut)
def create_license_word(payload: AdminLicenseWordCreate) -> AdminLicenseWordOut:
    session = _session()
    try:
        _get_family(session, payload.family_code)
        if payload.family_code == _NO_LICENSE_WORDS_FAMILY:
            raise HTTPException(
                status_code=422,
                detail=f"{_NO_LICENSE_WORDS_FAMILY} calcule sa licence directement dans le "
                        "code (resolver.build_fep_license) : un mot créé ici ne serait "
                        "jamais lu.",
            )
        word = LicenseWord(**payload.model_dump())
        session.add(word)
        session.commit()
        session.refresh(word)
        return _word_out(word)
    finally:
        session.close()


@router.put("/license-words/{word_id}", response_model=AdminLicenseWordOut)
def update_license_word(word_id: int, payload: AdminLicenseWordUpdate) -> AdminLicenseWordOut:
    session = _session()
    try:
        word = _get_word(session, word_id)
        word.label = payload.label
        word.position = payload.position
        session.commit()
        session.refresh(word)
        return _word_out(word)
    finally:
        session.close()


@router.delete("/license-words/{word_id}", status_code=204)
def delete_license_word(word_id: int) -> None:
    session = _session()
    try:
        word = _get_word(session, word_id)
        session.delete(word)
        session.commit()
    finally:
        session.close()


@router.post("/license-bits", response_model=AdminLicenseBitOut)
def create_license_bit(payload: AdminLicenseBitCreate) -> AdminLicenseBitOut:
    session = _session()
    try:
        word = _get_word(session, payload.word_id)
        options = _license_options(session, word.family_code, payload.option_ids)
        bit = LicenseBit(
            word_id=payload.word_id, position=payload.position, weight=payload.weight,
            label=payload.label, source_cell=payload.source_cell,
            unmapped_reason=payload.unmapped_reason, constant_value=payload.constant_value,
            options=options,
        )
        session.add(bit)
        session.commit()
        session.refresh(bit)
        return _bit_out(bit)
    finally:
        session.close()


@router.put("/license-bits/{bit_id}", response_model=AdminLicenseBitOut)
def update_license_bit(bit_id: int, payload: AdminLicenseBitUpdate) -> AdminLicenseBitOut:
    session = _session()
    try:
        bit = _get_bit(session, bit_id)
        options = _license_options(session, bit.word.family_code, payload.option_ids)
        bit.position = payload.position
        bit.weight = payload.weight
        bit.label = payload.label
        bit.source_cell = payload.source_cell
        bit.unmapped_reason = payload.unmapped_reason
        bit.constant_value = payload.constant_value
        bit.options = options
        session.commit()
        session.refresh(bit)
        return _bit_out(bit)
    finally:
        session.close()


@router.delete("/license-bits/{bit_id}", status_code=204)
def delete_license_bit(bit_id: int) -> None:
    session = _session()
    try:
        bit = _get_bit(session, bit_id)
        session.delete(bit)
        session.commit()
    finally:
        session.close()
