import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from catalogue import snowflake_client
from catalogue.agile_sync import sync_articles
from catalogue.database import SessionLocal, init_db
from catalogue.models import Article, OptionGroup, ProductFamily
from catalogue.resolver import build_license, check_rules, resolve_article
from catalogue.schemas import (
    ConfigurationRequest,
    ConfigurationResult,
    FamilyDetailOut,
    FamilyOut,
    SeedReport,
    SyncReport,
)
from catalogue.seed import load_catalogue

app = FastAPI(title="Catalogue Industriel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "snowflake_configured": snowflake_client.is_configured()}


@app.get("/api/families", response_model=list[FamilyOut])
def list_families() -> list[FamilyOut]:
    session: Session = SessionLocal()
    try:
        families = session.query(ProductFamily).order_by(ProductFamily.position).all()
        return [FamilyOut.model_validate(f, from_attributes=True) for f in families]
    finally:
        session.close()


@app.get("/api/families/{code}", response_model=FamilyDetailOut)
def get_family(code: str) -> FamilyDetailOut:
    session: Session = SessionLocal()
    try:
        family = session.get(ProductFamily, code)
        if family is None:
            raise HTTPException(status_code=404, detail=f"Gamme inconnue : {code}")
        return FamilyDetailOut.model_validate(family, from_attributes=True)
    finally:
        session.close()


@app.post("/api/configure", response_model=ConfigurationResult)
def configure(payload: ConfigurationRequest) -> ConfigurationResult:
    session: Session = SessionLocal()
    try:
        family = session.get(ProductFamily, payload.family_code)
        if family is None:
            raise HTTPException(status_code=404, detail=f"Gamme inconnue : {payload.family_code}")

        selected = set(payload.option_ids)
        # Une incompatibilité est une réponse, pas une panne : on la remonte telle quelle
        # pour que l'écran puisse l'afficher à côté de la configuration.
        violations = check_rules(session, family.code, selected)
        if violations:
            raise HTTPException(status_code=422, detail=violations)

        result = resolve_article(session, family.code, selected)

        if family.has_license:
            result["license"] = build_license(session, family.code, selected) or None

        # Un article que la synchro n'a jamais vu signale une grille à revoir côté IMI.
        if result["found"]:
            article = session.get(Article, result["item_number"])
            if not (article and article.last_sync):
                result["warnings"].append("Article absent du dernier import Agile.")
        return ConfigurationResult(**result)
    finally:
        session.close()


@app.post("/api/seed", response_model=SeedReport)
def seed() -> SeedReport:
    """Recharge la configuration depuis le classeur repris (`tools/import_workbook.py`).

    Ne touche pas aux articles : ceux-ci n'appartiennent qu'à la synchro Agile.
    """
    path = Path(os.getenv("CATALOGUE_SEED", "../data/catalogue.json"))
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"{path} absent — lancer d'abord tools/import_workbook.py.",
        )
    session: Session = SessionLocal()
    try:
        return SeedReport(**load_catalogue(session, path))
    finally:
        session.close()


@app.post("/api/sync", response_model=SyncReport)
def sync() -> SyncReport:
    if not snowflake_client.is_configured():
        raise HTTPException(
            status_code=503, detail="Identifiants Snowflake absents de l'environnement."
        )
    return SyncReport(**sync_articles())


@app.get("/api/articles/{item_number}")
def get_article(item_number: str) -> dict:
    session: Session = SessionLocal()
    try:
        article = session.get(Article, item_number)
        if article is None:
            raise HTTPException(status_code=404, detail=f"Article inconnu : {item_number}")
        return {
            "item_number": article.item_number,
            "description": article.description,
            "commercial_ref": article.commercial_ref,
            "product_line": article.product_line,
            "category": article.category,
            "lifecycle": article.lifecycle,
            "last_sync": article.last_sync,
        }
    finally:
        session.close()
