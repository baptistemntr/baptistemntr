"""Modèle de données du catalogue — voir docs/03-modele-de-donnees.md.

La structure suit celle du classeur, telle que la décrit `docs/04-regles-du-classeur.md` :
une gamme porte des options, chaque article déclare exactement les options qu'il embarque,
et la résolution compare la sélection à ces signatures.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Table, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from catalogue.database import Base


class Article(Base):
    """Miroir local d'un article Agile. Alimenté par la synchro, jamais édité à la main."""

    __tablename__ = "article"

    item_number: Mapped[str] = mapped_column(String(64), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text)
    commercial_ref: Mapped[str | None] = mapped_column(String(128))
    product_line: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(255))
    lifecycle: Mapped[str | None] = mapped_column(String(64))
    last_sync: Mapped[datetime | None] = mapped_column(DateTime)


class ProductFamily(Base):
    """Une gamme : CRT, HDR, DTR… (un onglet du classeur Excel)."""

    __tablename__ = "product_family"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    has_license: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    groups: Mapped[list["OptionGroup"]] = relationship(
        back_populates="family", cascade="all, delete-orphan", order_by="OptionGroup.position"
    )


class OptionGroup(Base):
    """Une question posée au commercial : Format, Panneau, Stockage…

    `single` traduit un groupe de boutons radio (`GroupName` partagé), `boolean` une case
    à cocher isolée. Un groupe exclusif peut n'avoir aucune réponse : le classeur propose
    souvent un choix neutre « None », qui ne coche aucune colonne.
    """

    __tablename__ = "option_group"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_code: Mapped[str] = mapped_column(ForeignKey("product_family.code"), nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    section: Mapped[str | None] = mapped_column(String(255))
    help_text: Mapped[str | None] = mapped_column(Text)
    # single | boolean
    selection: Mapped[str] = mapped_column(String(16), default="single")
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    family: Mapped[ProductFamily] = relationship(back_populates="groups")
    options: Mapped[list["Option"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", order_by="Option.position"
    )


class Option(Base):
    """Une réponse possible : C0, C1 IF, 4U…

    `caption` est le libellé historique du classeur : c'est lui qui relie l'option à sa
    colonne de grille, et il ne doit pas changer sans reprendre la grille. `label` est ce
    que voit le commercial, `technical_label` la définition affichée au survol — elle vient
    de la ligne « Commentaire » du classeur et répond au reproche de vocabulaire trop
    technique.

    `kind` distingue les options qui déterminent l'article (`grid`) de celles qui
    n'agissent que sur la licence (`license`) ou n'ont qu'une portée commerciale
    (`commercial`, ex. durée de licence, mode de livraison). Ces dernières ne participent
    pas à la résolution mais doivent figurer au récapitulatif.
    """

    __tablename__ = "option"
    __table_args__ = (UniqueConstraint("group_id", "caption"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("option_group.id"), nullable=False)
    caption: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    technical_label: Mapped[str | None] = mapped_column(Text)
    help_text: Mapped[str | None] = mapped_column(Text)
    # grid | license | commercial
    kind: Mapped[str] = mapped_column(String(16), default="grid")
    # Article Agile du composant apporté par l'option, et son prix — ligne 3 et 4 du
    # classeur. Le prix sert à estimer une configuration sans article existant.
    component_item_number: Mapped[str | None] = mapped_column(String(64))
    unit_price: Mapped[float | None] = mapped_column(Float)
    # Traçabilité vers le classeur, pour rejouer une comparaison en cas de doute.
    source_column: Mapped[int | None] = mapped_column(Integer)
    control_name: Mapped[str | None] = mapped_column(String(128))
    position: Mapped[int] = mapped_column(Integer, default=0)

    group: Mapped[OptionGroup] = relationship(back_populates="options")


class OptionRule(Base):
    """Compatibilité entre options — remplace les SI() imbriqués du classeur."""

    __tablename__ = "option_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_code: Mapped[str] = mapped_column(ForeignKey("product_family.code"), nullable=False)
    # requires | excludes
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    source_option_id: Mapped[int] = mapped_column(ForeignKey("option.id"), nullable=False)
    target_option_id: Mapped[int] = mapped_column(ForeignKey("option.id"), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)


# Les options qu'un article embarque — l'ensemble forme sa signature.
mapping_option = Table(
    "mapping_option",
    Base.metadata,
    Column("mapping_id", ForeignKey("article_mapping.id"), primary_key=True),
    Column("option_id", ForeignKey("option.id"), primary_key=True),
)


class ArticleMapping(Base):
    """Une ligne de la grille : un article et la combinaison d'options qui le désigne.

    `item_number` n'est volontairement pas une clé étrangère vers `article` : la grille
    est tenue par l'IMI et peut citer un article absent du dernier import Agile. Cet écart
    se signale, il ne doit pas empêcher l'enregistrement (cf. docs/02-architecture.md).

    `designation`, `commercial_ref` et `standard_price` reprennent ce que le classeur
    affiche aujourd'hui ; ils servent de repli tant qu'Agile n'a pas été synchronisé, et
    de point de comparaison ensuite.
    """

    __tablename__ = "article_mapping"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_code: Mapped[str] = mapped_column(ForeignKey("product_family.code"), nullable=False)
    item_number: Mapped[str | None] = mapped_column(String(64))
    designation: Mapped[str | None] = mapped_column(Text)
    commercial_ref: Mapped[str | None] = mapped_column(String(128))
    standard_price: Mapped[float | None] = mapped_column(Float)
    # Signature normalisée (captions triées) : la résolution est une égalité stricte.
    signature: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_row: Mapped[int | None] = mapped_column(Integer)

    options: Mapped[list[Option]] = relationship(secondary=mapping_option)


class LicenseWord(Base):
    """Un mot de licence : DEM1 (par démodulateur), DEMLI (global), MODLI (modulateur).

    Le classeur en produit plusieurs par gamme. Chacun est une somme pondérée de bits,
    rendue en hexadécimal — c'est exactement ce que fait
    `DEC2HEX(SUMIF(valeurs; VRAI; poids))` dans l'onglet « Licences <Gamme> ».
    """

    __tablename__ = "license_word"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_code: Mapped[str] = mapped_column(ForeignKey("product_family.code"), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    bits: Mapped[list["LicenseBit"]] = relationship(
        back_populates="word", cascade="all, delete-orphan", order_by="LicenseBit.position"
    )


# Certains bits dépendent de plusieurs options à la fois (ex. MODLI!D6 = 4D-TCM OU 6D-TCM
# OU 6D-TCM-DSNG) : la table associative porte la sémantique « au moins une cochée ».
license_bit_option = Table(
    "license_bit_option",
    Base.metadata,
    Column("bit_id", ForeignKey("license_bit.id"), primary_key=True),
    Column("option_id", ForeignKey("option.id"), primary_key=True),
)


class LicenseBit(Base):
    """Un bit d'un mot de licence : ajoute son poids si au moins une option associée est
    retenue (OR — le seul opérateur employé par le classeur pour combiner plusieurs options
    sur un même bit).

    Certains bits du classeur dépendent d'un compteur numérique (nombre de MODCODs, nombre
    d'unités de modulation...) plutôt que d'une option cochée — notre modèle ne représente
    que des choix discrets, pas ces quantités. Un tel bit n'a aucune option associée et
    porte `unmapped_reason` : il compte toujours pour 0 plutôt que de fausser la clé
    silencieusement.
    """

    __tablename__ = "license_bit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("license_word.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    # Cellule(s) d'origine dans le classeur, pour pouvoir rejouer le calcul.
    source_cell: Mapped[str | None] = mapped_column(String(64))
    unmapped_reason: Mapped[str | None] = mapped_column(Text)

    word: Mapped[LicenseWord] = relationship(back_populates="bits")
    options: Mapped[list[Option]] = relationship(secondary=license_bit_option)
