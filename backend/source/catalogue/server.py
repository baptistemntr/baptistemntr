from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from catalogue import snowflake_client
from catalogue.agile_sync import sync_articles
from catalogue.database import SessionLocal, init_db
from catalogue.models import Article, OptionGroup, ProductFamily
from catalogue.resolver import ConfigurationError, build_license, check_rules, resolve_article
from catalogue.schemas import (
    ConfigurationRequest,
    ConfigurationResult,
    FamilyDetailOut,
    FamilyOut,
    SyncReport,
)

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
        violations = check_rules(session, family.code, selected)
        if violations:
            raise HTTPException(status_code=422, detail=violations)

        try:
            result = resolve_article(session, family.code, selected)
        except ConfigurationError as exc:
            raise HTTPException(status_code=422, detail=[str(exc)]) from exc

        if family.has_license:
            result["license"] = build_license(session, family.code, selected) or None

        # Un article non synchronisé récemment signale une grille à revoir côté IMI.
        article = session.get(Article, result["item_number"])
        result["warnings"] = (
            [] if article and article.last_sync else ["Article absent du dernier import Agile."]
        )
        return ConfigurationResult(**result)
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
