# Architecture

## 1. Principe directeur

Le classeur Excel mélange trois choses dans les mêmes cellules : **les données produit**
(qui viennent d'Agile), **les règles de configuration** (qui appartiennent à l'IMI) et
**la présentation** (qui appartient au commercial). Tout le coût de maintenance vient de
ce mélange.

La nouvelle architecture les sépare :

```
   Agile PLM                Configuration IMI            Interface commerciale
  (via Snowflake)            (base + écrans)                 (web)
        │                          │                            │
        │  articles, désignations  │  gammes, options,          │  choix guidés,
        │  références, cycle de vie│  grille de croix,          │  récapitulatif,
        │  ← synchro automatique   │  règles de licence         │  export client
        └──────────────┬───────────┴──────────────┬─────────────┘
                       ▼                          ▼
                  API catalogue (FastAPI)     Front statique
```

Conséquence directe : **ajouter une gamme ou une option ne demande aucun développement**,
uniquement de la saisie dans l'écran d'administration IMI.

## 2. Composants

### `backend/` — API catalogue (Python / FastAPI)

Reprend exactement le patron de l'**agent Agile** déjà en production :

- authentification Snowflake par **paire de clés RSA** (`snowflake-connector-python`),
- variables d'environnement dans `.env`, clé privée montée dans `secrets/`,
- base applicative PostgreSQL (SQLite en développement) via SQLAlchemy,
- conteneurisation Docker, déploiement derrière le proxy Safran.

Responsabilités :

| Rôle | Détail |
|------|--------|
| Synchro Agile | Miroir local des articles (`ITEM`, classe 10000) rafraîchi périodiquement |
| Référentiel de configuration | Gammes, groupes d'options, options, grille article, règles de compatibilité |
| Résolution | Combinaison d'options → article Agile + désignation + référence commerciale |
| Licences | Génération de la clé à partir des bits déclarés pour la gamme |
| Export | Récapitulatif de configuration (PDF / fiche client), avec un code de reprise |

### `frontend/` — Interface (HTML/CSS/JS sans framework)

Même choix technique que le *CDS analyzer* : pas de build, pas de dépendance externe,
un dossier statique déployable tel quel derrière le proxy Safran.

Deux espaces :

- **Espace commercial** : sélection de la gamme, configuration guidée, récapitulatif
  permanent en haut d'écran, infobulles sur chaque terme, export de la fiche client (PDF via
  impression navigateur — sans donnée structurée embarquée, juste du texte imprimé). Reprise
  fiable d'une fiche exportée : un code compact (`<gamme>:<ids d'options>`, ex.
  `CRT:101,203,304`) est imprimé au bas de chaque fiche, à recopier dans le champ « Reprendre
  une configuration exportée » pour recocher exactement les mêmes options — pas de lecture
  automatique du PDF (nécessiterait une nouvelle dépendance Python d'extraction, écartée
  pour rester sans installation supplémentaire sur les postes verrouillés).
- **Espace IMI** (`/admin.html`) : administration des gammes, options, textes d'aide,
  grille de croix et règles de licence — l'équivalent des onglets « settings », mais sans
  formule cachée. V1 restreinte à une gamme pilote, licences hors périmètre — voir
  `docs/06-admin-imi.md`.

### `tools/` — Outillage de reprise

- `inspect_excel.py` : cartographie du classeur existant (onglets, zones, formules,
  grilles de croix) pour préparer la migration.
- `discover_agile.py` : exploration Snowflake pour identifier les colonnes et attributs
  `AGILE_FLEX` qui portent la référence commerciale et le cycle de vie.

## 3. Connexion Snowflake

Identique à l'agent Agile :

| Paramètre | Valeur |
|-----------|--------|
| Compte | `safran-sed_space` |
| Hôte | `safran-sed_space.privatelink.snowflakecomputing.com` |
| Utilisateur de service | `GS3_SERVICE_USER` |
| Rôle | `RF_GS3_ANALYST` |
| Warehouse | `WH_GS3` |
| Base / schéma | `PRD_RAW_PLM_AGILE` / `AGILE` |
| Authentification | clé privée RSA `rsa_GS4_key.p8` + passphrase |

La clé et la passphrase **ne sont pas versionnées** : la clé se dépose dans
`backend/secrets/`, la passphrase dans `.env` (les deux sont exclus par `.gitignore`).

## 4. Stratégie de synchronisation

La synchro est **descendante et non destructive** : Agile est la source de vérité pour les
*articles*, jamais pour la *configuration*.

1. Un scan périodique lit les articles de classe 10000 (Pièces) dans Snowflake.
2. Chaque article est inséré ou mis à jour dans la table miroir `article`.
3. La grille IMI référence les articles **par leur `item_number`**, pas par une copie de
   leur désignation. Un changement de libellé côté Agile se propage donc tout seul.
4. Les entrées de la grille dont l'article n'existe plus (ou est sorti de production) sont
   **signalées à l'IMI**, jamais supprimées automatiquement.

C'est ce point 4 qui remplace la relecture manuelle du classeur : l'outil dit lui-même ce
qui a bougé depuis la dernière fois.

## 5. Modèle de données

Voir `03-modele-de-donnees.md`.
