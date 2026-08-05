"""Espace IMI : édition directe du référentiel (gammes, groupes, options, grille, règles).

Remplace, pour ce qui est couvert, le passage obligé par `tools/import_workbook.py` et le
classeur Excel — c'est tout l'objet de cet écran (voir docs/02-architecture.md § 2).
Périmètre V1, volontairement restreint pour valider le modèle avant de généraliser :

- une seule gamme pilote (`DTR`, voir docs/06-admin-imi.md) ;
- pas d'édition des licences (mots/bits) ni création de nouvelle gamme ;
- `Option.caption` et `OptionGroup.code` ne se fixent qu'à la création : ce sont les clés
  stables dont dépend la résolution (`resolver.signature_of`), les renommer casserait
  silencieusement la grille — voir `docs/04-regles-du-classeur.md` § 3.

Protégé par un mot de passe partagé (HTTP Basic, `ADMIN_PASSWORD`) : c'est un espace
d'écriture sur ce que voient les commerciaux, pas la configuration en lecture seule.
"""

import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from catalogue.database import SessionLocal
from catalogue.models import ArticleMapping, Option, OptionGroup, OptionRule, ProductFamily
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
    AdminOptionCreate,
    AdminOptionOut,
    AdminOptionUpdate,
    AdminRuleCreate,
    AdminRuleOut,
    FamilyOut,
)

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
        return AdminFamilyDetailOut(
            code=family.code, label=family.label, description=family.description,
            has_license=family.has_license,
            groups=[AdminGroupOut.model_validate(g, from_attributes=True) for g in family.groups],
            articles=[_article_out(a) for a in articles],
            rules=[AdminRuleOut.model_validate(r, from_attributes=True) for r in rules],
        )
    finally:
        session.close()


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
