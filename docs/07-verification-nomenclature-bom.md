# Vérification nomenclature Agile (BOM) — note pour la réunion IMI

> Produit par le panneau « Vérification nomenclature Agile (BOM) » de l'espace IMI
> (`catalogue.bom_check`, endpoint `GET /api/admin/families/{code}/bom-check`). Compare,
> pour chaque ligne de la grille, le composant Agile attendu de chaque option cochée
> (`Option.component_item_number`) avec la nomenclature (BOM) réelle de l'article dans
> Snowflake. Comme pour `docs/05-diagnostic-classeur.md`, ce document signale des points à
> arbitrer avec l'IMI — rien n'est corrigé d'office.

## Ce que fait la vérification

Pour chaque article de la grille dont l'`item_number` est connu, l'outil récupère sa
nomenclature active (`BOM.CHANGE_OUT = 0`) via Snowflake, et vérifie que le composant
attendu de chaque option cochée y figure. Les `component_item_number` qui ne ressemblent
pas à un vrai code Agile (texte libre du classeur, ex. `S120657+cables+meca`, `3 * S119519`)
sont exclus du périmètre vérifiable — ils ne sont ni signalés comme une anomalie, ni comptés
faussement comme un écart (voir `_JUNK_COMPONENT_RE` dans `bom_check.py`).

## Premier passage réel — gamme CRT (20/08/2026)

**92 écarts** avant filtrage du texte libre, **49** après (`Option.component_item_number`
propre mais absent de la nomenclature réelle). Sur ces 49, quatre situations distinctes se
dégagent — à ne pas traiter comme 49 problèmes identiques.

### 1. Composant de l'option C0 potentiellement obsolète (2 codes concernés)

`Option.component_item_number` de C0 vaut `S128865` (« MODULE MERE-ANA CRT-2U PCC »).
Attendu : présent sur les configurations 4U *et* 2U selon une logique de variante. Constaté :
absent des deux.

- **S128354** (CRT-PCC-C0-4U) : nomenclature réelle contient `S144191`
  (« MODULE MERE-ANA 4U PCC EQUIPE »), pas `S128865`.
- **S128356** (CRT-PCC-C0-2U — c'est pourtant déjà la variante 2U) : nomenclature réelle
  contient `S144190`, pas `S128865` non plus.

`S144190`/`S144191` semblent être les remplaçants actuels de `S128865`, pour les deux
formats de châssis. **Question pour l'IMI** : `S128865` est-il toujours un composant valide,
ou faut-il mettre à jour la grille vers `S144190`/`S144191` (2U/4U respectivement) ?

### 2. Composant de l'option C1 systématiquement absent (~20 lignes concernées)

`Option.component_item_number` de C1 vaut `S126299`. Il n'apparaît dans **aucune** des
nomenclatures réelles vérifiées, ni en 2U ni en 4U — tous formats et toutes variantes
confondus (P3U, P2U, +4TB, COP, FIB, PVB6...). Deux codes reviennent en revanche de façon
très cohérente :

- **`S135951`** sur toutes les configurations 4U de C1
- **`S135952`** sur toutes les configurations 2U de C1

**Question pour l'IMI** : `S126299` est-il une référence périmée pour l'option C1,
remplacée par `S135951` (4U) / `S135952` (2U) ? C'est le même schéma que le point 1
(remplacement produit), mais qui touche une bien plus grande part du catalogue CRT.

### 3. L'option « C1 IF » recopie le composant de « C1 » plutôt que d'avoir le sien

`C1 IF` porte le même `component_item_number` (`S126299`) que `C1` simple. Or `C0 IF`
(l'équivalent sans IF) a bien son propre composant distinct (`S129698`, différent de celui
de `C0`). Ça ressemble à une saisie non mise à jour plutôt qu'un choix délibéré.
**Question pour l'IMI** : `C1 IF` doit-il avoir un composant propre (probablement une
variante de `S135951`/`S135952` avec IF), au lieu de recopier celui de `C1` ?

### 4. PVB sur les articles « PVB6 » (6 lignes)

`Option.component_item_number` de PVB vaut `S140598`, absent des 6 nomenclatures réelles
des articles `*+PVB6+*`. Probablement le même schéma que les points 1-2 : `S140598` daterait
d'avant l'introduction de la variante « PVB6 ». **Question pour l'IMI** : quel est le bon
composant pour cette variante ?

### 5. Faux positifs structurels — pas une vraie anomalie (les lignes « SECU »)

Les articles `CRT-PCC-SECU-*` (ex. `S139167`, `S140392`...) ont une nomenclature très
courte qui référence directement d'autres articles déjà assemblés (ex. `S128355`,
`S139168`, `S140400`) plutôt que des composants bruts — un niveau de nomenclature que la
vérification actuelle ne traverse pas. Les écarts remontés sur ces lignes (composants de
C0/C1 et des panneaux) sont un effet de bord de cette limite, pas un signal réel. À ignorer
tant que la vérification ne sait pas descendre d'un niveau de nomenclature.

## Synthèse à emporter en réunion

Sur les 49 écarts, l'essentiel se ramène à **deux composants potentiellement obsolètes dans
la grille** (celui de C0, celui de C1 — ce dernier touchant la quasi-totalité des articles
C1 de la gamme CRT) plutôt qu'à 49 problèmes distincts, plus un point de saisie probable
(C1 IF) et une variante récente non mise à jour (PVB6). Les lignes SECU sont à mettre de
côté (limite connue de l'outil, pas une anomalie produit).

## Prochaines étapes possibles (hors périmètre de cette note)

- Étendre la vérification aux autres gammes (aujourd'hui : CRT uniquement, testé
  manuellement depuis l'espace IMI).
- Faire traverser un niveau de nomenclature supplémentaire pour les articles « kit de
  kits » (SECU), afin d'éliminer les faux positifs du point 5.
- Une fois les composants obsolètes tranchés par l'IMI, mettre à jour les
  `component_item_number` concernés dans l'espace IMI (édition d'option, déjà possible
  sans développement).
