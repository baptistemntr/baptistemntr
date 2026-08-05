# Catalogue Industriel

Refonte du catalogue industriel Safran — aujourd'hui un classeur Excel géré par les IMI et
utilisé par les commerciaux pour configurer un produit et obtenir la référence à commander.

Deux objectifs, dans cet ordre :

1. **Supprimer la ressaisie manuelle** en alimentant le catalogue depuis Agile via Snowflake.
2. **Rendre l'outil utilisable par un commercial** sans accompagnement : vocabulaire
   explicité, configuration guidée, récapitulatif exportable pour le client.

Contrainte ferme : **aucune régression**. Le nouvel outil doit faire au moins autant que le
classeur actuel, sans rien masquer de l'information existante.

## Documentation

| Document | Contenu |
|----------|---------|
| [Contexte et besoin](docs/01-contexte-et-besoin.md) | Restitution du cadrage avec l'IMI — référence fonctionnelle |
| [Architecture](docs/02-architecture.md) | Découpage des composants, connexion Snowflake, stratégie de synchro |
| [Modèle de données](docs/03-modele-de-donnees.md) | Traduction du classeur en tables explicites |
| [Règles du classeur](docs/04-regles-du-classeur.md) | Ce que fait réellement le classeur — rétro-ingénierie du VBA et des onglets |
| [Diagnostic du classeur](docs/05-diagnostic-classeur.md) | Anomalies héritées, à trancher avec l'IMI |

## Structure

```
Catalogue Industriel/
├── backend/                 API FastAPI + synchro Snowflake
│   ├── source/catalogue/
│   │   ├── snowflake_client.py   Connexion Agile (clé RSA, cf. agent Agile)
│   │   ├── agile_sync.py         Miroir local des articles
│   │   ├── models.py             Gammes, options, grille, licences
│   │   ├── resolver.py           Configuration → article + clé de licence
│   │   └── server.py             Endpoints REST
│   ├── secrets/             Clé privée Snowflake (non versionnée)
│   └── .env.example
├── frontend/                Interface commerciale (HTML/CSS/JS, sans build)
│   ├── index.html
│   ├── css/style.css
│   └── js/{api,app}.js
├── tools/
│   ├── inspect_excel.py     Cartographie du classeur existant
│   └── discover_agile.py    Exploration du schéma Agile dans Snowflake
└── data/                    Classeur de référence (non versionné)
```

## Démarrage

```bash
cd backend && pip install -r requirements.txt && pip install -e .
```

```bash
cp backend/.env.example backend/.env
```

Déposer la clé privée Snowflake dans `backend/secrets/rsa_GS4_key.p8`, renseigner la
passphrase dans `.env`, puis lancer l'API :

```bash
cd backend && python -m uvicorn catalogue.server:app --reload --port 8010
```

Documentation interactive : http://localhost:8010/docs

L'API démarre même sans accès Snowflake ; seule la route `/api/sync` est alors indisponible.

## Reprise du classeur existant

Déposer le classeur dans `data/`, puis :

```bash
python3 tools/import_workbook.py "data/Catalogue industriel.xlsm" \
    --sortie data/catalogue.json --rapport docs/05-diagnostic-classeur.md
```

Charger le résultat dans la base (`POST /api/seed`), puis vérifier la non-régression :

```bash
cd backend && PYTHONPATH=source python -m pytest tests/ -q
```

Pour les licences (HDR seulement pour l'instant) :

```bash
python3 tools/import_licenses.py --sortie data/licenses.json
```

Puis charger via `POST /api/seed-licenses` (après `/api/seed`, les bits référencent des
options qui doivent déjà exister).

Deux outils d'exploration restent disponibles : `tools/inspect_excel.py` (cartographie
brute d'un onglet) et `tools/extract_controls.py` (libellés et groupes des contrôles).

## Interface commerciale

```bash
cd frontend && python3 -m http.server 5500
```

Ouvrir http://localhost:5500 (le backend doit tourner sur le port 8010). Détails dans
`frontend/README.md`.

## État d'avancement

- [x] Cadrage fonctionnel documenté
- [x] Connexion Snowflake (patron repris de l'agent Agile)
- [x] Modèle de données et moteur de résolution
- [x] Outils de reprise du classeur
- [x] Analyse du classeur de référence → import des 19 gammes, 171 options, 306 articles
- [x] Non-régression vérifiée : 306/306 lignes de la grille résolues à l'identique
- [x] Formule de licence identifiée (somme pondérée de bits → hexadécimal)
- [x] Interface commerciale (V1) : choix de gamme, configuration guidée, récapitulatif
  permanent, infobulles, export par impression — vérifiée dans un navigateur
- [x] Licences HDR peuplées (`tools/import_licenses.py`) : 48/61 bits calculés (directs ou
  OU entre options), 13 signalés (compteurs numériques non modélisés, 2 anomalies
  d'import) — voir `docs/04-regles-du-classeur.md` § 4
- [x] Licence CRT (FEP) peuplée (`resolver.build_fep_license`) : table de 11 fonctions +
  5 compteurs matériels (pas une somme pondérée comme HDR), numéro de dongle calculé —
  voir `docs/04-regles-du-classeur.md` § 4. Une fonction (« TC Spacebus ») reste signalée,
  sans contrôle sur l'écran CRT pour la piloter.
- [x] Licence SATCORE peuplée (`tools/import_licenses.py`, mots DEM/DEMLI, 37 bits) : la
  plupart des bits sont des constantes du classeur (aucun contrôle, base toujours incluse),
  seuls 3 dépendent réellement d'une option ; le mot DEMLI est entièrement figé (`0x2E`) —
  voir `docs/04-regles-du-classeur.md` § 4. 4 bits signalés (constantes référencées sans
  contrôle pour les activer, même anomalie que HDR).
- [x] Synchro Agile réelle exécutée (`POST /api/sync`) : 119 624 articles importés, jointure
  CATEGORY/PRODUCT_LINES vérifiée sur de vraies données avant le lancement
  (`tools/discover_agile.py --preview-sync`), avertissement « Article absent du dernier
  import Agile » confirmé disparu côté commercial pour un article synchronisé.
- [ ] Correspondance bit → option d'HDR, CRT et SATCORE à rejouer sur une licence réellement
  émise
- [ ] Identification de l'attribut « référence commerciale » dans Agile — localisé côté UI
  Agile (« Safran Sales Reference », onglet Sales - Export Control), introuvable via
  Snowflake malgré exploration systématique ; probablement à accès restreint (export
  control). Prochaine étape : demander l'ATTID à un administrateur Agile.
- [ ] Cycle de vie (`Article.lifecycle`) : jamais rempli, trois pistes explorées sans succès
  (`VERSION.LIFECYCLEPHASE`, `REV.RELEASE_TYPE`, `CHANGE.STATUSTYPE`) — même impasse que la
  référence commerciale, même recommandation : demander à un administrateur Agile.
- [ ] Arbitrage des 129 anomalies héritées avec l'IMI
- [x] Écran d'administration IMI : `/admin.html`, protégé par mot de passe
  (`ADMIN_PASSWORD`), les 19 gammes éditables — libellés commerciaux (répond au point
  ci-dessous), grille, règles de compatibilité, et mots/bits de licence HDR/SATCORE.
  Création de gamme et licence CRT (codée en dur, pas en base) hors périmètre — voir
  `docs/06-admin-imi.md`. Confirmé par recherche Snowflake : rien à synchroniser
  automatiquement depuis Agile pour les valeurs de licence (dépendent de la config
  commandée, pas un attribut fixe d'article).
- [ ] Libellés de groupe commerciaux (certains affichent encore le `GroupName` technique du
  classeur, ex. `CRT_options_panneau`) — éditables dès aujourd'hui via l'écran d'admin, à
  passer en revue avec l'IMI
- [ ] Export à un autre format que l'impression navigateur
