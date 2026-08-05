# Modèle de données

Le modèle traduit littéralement la structure du classeur Excel, mais en tables explicites
plutôt qu'en formules cachées.

| Objet Excel | Objet du modèle |
|-------------|-----------------|
| Un onglet gamme (CRT, HDR…) | `product_family` |
| Une colonne de choix (Format, Panneau, Stockage…) | `option_group` |
| Une valeur de choix (`4U`, `C0`, `C1 IF`…) | `option` |
| Une croix dans la grille | `article_mapping` |
| L'onglet « settings » (codes articles) | `article`, alimenté depuis Snowflake |
| L'onglet licence (matrice de 1 et 0) | `license_bit` |

## Tables

### `article` — miroir Agile (lecture seule)

Alimenté par la synchro Snowflake. Jamais édité à la main.

| Champ | Type | Source Agile |
|-------|------|--------------|
| `item_number` | `str` (PK) | `ITEM.ITEM_NUMBER` — le code article (`S…`) |
| `description` | `str` | `ITEM.DESCRIPTION` — la désignation |
| `commercial_ref` | `str?` | `AGILE_FLEX` — attribut à identifier (voir `discover_agile.py`) |
| `product_line` | `str?` | `LISTENTRY` via `ITEM.PRODUCT_LINES` |
| `category` | `str?` | `LISTENTRY` via `ITEM.CATEGORY` |
| `lifecycle` | `str?` | cycle de vie — jamais rempli, source Agile introuvable (voir `docs/01-contexte-et-besoin.md` § 5) |
| `last_sync` | `datetime` | horodatage de la dernière synchro |

### `product_family` — une gamme

| Champ | Type | Rôle |
|-------|------|------|
| `code` | `str` (PK) | `CRT`, `HDR`, `DTR`… |
| `label` | `str` | Nom commercial affiché |
| `description` | `str?` | Texte d'introduction pour le commercial |
| `has_license` | `bool` | La gamme génère-t-elle une clé de licence |
| `position` | `int` | Ordre d'affichage |

### `option_group` — une question posée au commercial

| Champ | Type | Rôle |
|-------|------|------|
| `id` | `int` (PK) | |
| `family_code` | `str` (FK) | Gamme concernée |
| `code` | `str` | `FORMAT`, `PANNEAU`, `STOCKAGE`… |
| `label` | `str` | Libellé commercial de la question |
| `help_text` | `str?` | Texte de l'infobulle (résout le point P3 du besoin) |
| `selection` | `enum` | `single` \| `multiple` \| `boolean` |
| `required` | `bool` | |
| `position` | `int` | |

### `option` — une réponse possible

| Champ | Type | Rôle |
|-------|------|------|
| `id` | `int` (PK) | |
| `group_id` | `int` (FK) | |
| `code` | `str` | Le code métier historique : `C0`, `C1 IF`, `4U`… |
| `label` | `str` | Le libellé **commercial** — ce que voit l'utilisateur |
| `technical_label` | `str?` | La définition technique : « carte mère PC + carte AN » |
| `help_text` | `str?` | Explication longue affichée en popup |
| `position` | `int` | |

> Le triplet `code` / `label` / `technical_label` est la réponse directe au problème
> « ce n'est pas assez commercial » : le code reste disponible pour l'IMI, le libellé
> commercial est ce qui s'affiche, la définition technique est à un survol de souris.

### `option_rule` — compatibilités

Remplace les formules `SI(...)` imbriquées du classeur.

| Champ | Type | Rôle |
|-------|------|------|
| `id` | `int` (PK) | |
| `family_code` | `str` (FK) | |
| `kind` | `enum` | `requires` \| `excludes` |
| `source_option_id` | `int` (FK) | |
| `target_option_id` | `int` (FK) | |
| `message` | `str?` | Message affiché au commercial si la règle bloque |

### `article_mapping` — la grille de croix

| Champ | Type | Rôle |
|-------|------|------|
| `id` | `int` (PK) | |
| `family_code` | `str` (FK) | |
| `option_ids` | `list[int]` | La combinaison d'options qui désigne cet article |
| `item_number` | `str` (FK → `article`) | Le code article Agile résultant |
| `override_label` | `str?` | Désignation forcée si celle d'Agile ne convient pas |

La résolution prend la combinaison choisie par le commercial et retourne le mapping dont
`option_ids` est **inclus** dans la sélection, le plus spécifique gagnant. Désignation et
référence commerciale sont ensuite lues dans `article`, donc toujours à jour.

### `license_bit` — génération de clé

Traduction de la matrice binaire des onglets licence.

| Champ | Type | Rôle |
|-------|------|------|
| `id` | `int` (PK) | |
| `family_code` | `str` (FK) | |
| `position` | `int` | Rang du bit dans la clé |
| `option_id` | `int?` (FK) | Le bit vaut 1 si cette option est sélectionnée |
| `label` | `str` | Nom de la fonction licenciée |

L'encodage final (longueur, base, séparateurs, checksum éventuel) sera fixé après
rétro-ingénierie de l'onglet licence du classeur — c'est le seul point du modèle qui
attend encore le fichier source.

## Ce que le modèle apporte concrètement

- **Aucune formule cachée** : une croix est une ligne de table, une règle est une ligne de table.
- **Désignations jamais recopiées** : elles sont résolues depuis le miroir Agile.
- **Extensible sans code** : une nouvelle gamme = des insertions, pas un nouvel onglet.
- **Auditable** : on peut répondre à « pourquoi cet article a-t-il été proposé ? ».
