"""Modèle de données du catalogue — voir docs/03-modele-de-donnees.md."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Table, Text, Column
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
    """Une question posée au commercial : Format, Panneau, Stockage…"""

    __tablename__ = "option_group"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_code: Mapped[str] = mapped_column(ForeignKey("product_family.code"), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    help_text: Mapped[str | None] = mapped_column(Text)
    # single | multiple | boolean
    selection: Mapped[str] = mapped_column(String(16), default="single")
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    family: Mapped[ProductFamily] = relationship(back_populates="groups")
    options: Mapped[list["Option"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", order_by="Option.position"
    )


class Option(Base):
    """Une réponse possible : C0, C1 IF, 4U…

    `code` est le code métier historique, `label` ce que voit le commercial,
    `technical_label` la définition technique affichée au survol.
    """

    __tablename__ = "option"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("option_group.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    technical_label: Mapped[str | None] = mapped_column(Text)
    help_text: Mapped[str | None] = mapped_column(Text)
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


# Une croix de la grille peut porter sur plusieurs options simultanément.
mapping_option = Table(
    "mapping_option",
    Base.metadata,
    Column("mapping_id", ForeignKey("article_mapping.id"), primary_key=True),
    Column("option_id", ForeignKey("option.id"), primary_key=True),
)


class ArticleMapping(Base):
    """Une croix de la grille : une combinaison d'options désigne un article Agile."""

    __tablename__ = "article_mapping"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_code: Mapped[str] = mapped_column(ForeignKey("product_family.code"), nullable=False)
    item_number: Mapped[str] = mapped_column(ForeignKey("article.item_number"), nullable=False)
    override_label: Mapped[str | None] = mapped_column(Text)

    options: Mapped[list[Option]] = relationship(secondary=mapping_option)
    article: Mapped[Article] = relationship()


class LicenseBit(Base):
    """Un bit de la clé de licence : vaut 1 si l'option associée est sélectionnée."""

    __tablename__ = "license_bit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_code: Mapped[str] = mapped_column(ForeignKey("product_family.code"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    option_id: Mapped[int | None] = mapped_column(ForeignKey("option.id"))
    label: Mapped[str] = mapped_column(String(255), nullable=False)
