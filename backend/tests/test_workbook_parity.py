"""Non-régression : le moteur doit rendre ce que rend le classeur.

La contrainte posée par l'IMI est qu'aucune configuration ne se comporte moins bien
qu'aujourd'hui. On la vérifie de la façon la plus directe possible : chaque ligne de la
grille est rejouée comme si un commercial avait coché exactement ses options, et doit
retourner l'article de cette ligne.

Les tests s'appuient sur `data/catalogue.json`, produit par `tools/import_workbook.py`.
Ce fichier dérive du classeur, qui n'est pas versionné : à défaut, les tests sont ignorés.
"""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from catalogue.database import Base
from catalogue.models import ArticleMapping, Option, ProductFamily
from catalogue.resolver import resolve_article, signature_of
from catalogue.seed import load_catalogue

CATALOGUE = Path(__file__).resolve().parents[2] / "data" / "catalogue.json"


@pytest.fixture(scope="module")
def session():
    if not CATALOGUE.exists():
        pytest.skip(f"{CATALOGUE} absent — lancer tools/import_workbook.py")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    load_catalogue(session, CATALOGUE)
    yield session
    session.close()


def test_le_catalogue_est_charge(session):
    assert session.query(ProductFamily).count() > 0
    assert session.query(ArticleMapping).count() > 0


def test_chaque_ligne_de_la_grille_retrouve_son_article(session):
    """Aucune ligne ne doit devenir irrésolvable : ce serait une régression franche."""
    unresolved = []
    for mapping in session.query(ArticleMapping).all():
        result = resolve_article(session, mapping.family_code,
                                 {o.id for o in mapping.options})
        if not result["found"]:
            unresolved.append((mapping.family_code, mapping.item_number, mapping.signature))
    assert unresolved == []


def test_les_lignes_de_signature_unique_rendent_leur_propre_article(session):
    """Seules les combinaisons en double peuvent renvoyer un autre article.

    Le classeur retient la première ligne trouvée et ignore les suivantes ; on reproduit
    ce choix, mais le doublon est signalé au lieu d'être silencieux.
    """
    counts: dict[tuple[str, str], int] = {}
    for mapping in session.query(ArticleMapping).all():
        key = (mapping.family_code, mapping.signature)
        counts[key] = counts.get(key, 0) + 1

    for mapping in session.query(ArticleMapping).all():
        if counts[(mapping.family_code, mapping.signature)] > 1:
            continue
        result = resolve_article(session, mapping.family_code,
                                 {o.id for o in mapping.options})
        assert result["item_number"] == mapping.item_number
        assert result["warnings"] == []


def test_une_combinaison_partielle_ne_renvoie_pas_un_article_approchant(session):
    """La correspondance est stricte, comme dans le VBA.

    Retirer une option d'une combinaison valide ne doit pas faire ressortir un article
    « presque bon » : le classeur renvoie « See Manufacturing », et proposer autre chose
    serait un contresens commercial.
    """
    mapping = (
        session.query(ArticleMapping)
        .filter(ArticleMapping.family_code == "CRT")
        .filter(ArticleMapping.signature.contains("|"))
        .first()
    )
    options = list(mapping.options)
    partial = {o.id for o in options[:-1]}
    signatures = {m.signature for m in session.query(ArticleMapping)
                  .filter_by(family_code="CRT").all()}
    if signature_of({o.caption for o in options[:-1]}) in signatures:
        pytest.skip("la combinaison réduite existe aussi dans la grille")

    result = resolve_article(session, "CRT", partial)
    assert result["found"] is False
    assert result["item_number"] == "Doesn't exist"
    assert result["closest"]  # on explique quand même ce qui s'en rapproche


def test_les_options_hors_grille_ne_changent_pas_l_article(session):
    """Cocher une licence ne doit pas modifier la référence à commander."""
    mapping = (
        session.query(ArticleMapping)
        .filter(ArticleMapping.family_code == "CRT", ArticleMapping.item_number.isnot(None))
        .first()
    )
    base = {o.id for o in mapping.options}
    licences = (
        session.query(Option)
        .join(Option.group)
        .filter(Option.kind == "license")
        .limit(2)
        .all()
    )
    result = resolve_article(session, "CRT", base | {o.id for o in licences})
    assert result["item_number"] == mapping.item_number
