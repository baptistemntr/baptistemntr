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
├── frontend/                Interface commerciale + administration IMI
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

Deux outils d'exploration restent disponibles : `tools/inspect_excel.py` (cartographie
brute d'un onglet) et `tools/extract_controls.py` (libellés et groupes des contrôles).

## État d'avancement

- [x] Cadrage fonctionnel documenté
- [x] Connexion Snowflake (patron repris de l'agent Agile)
- [x] Modèle de données et moteur de résolution
- [x] Outils de reprise du classeur
- [x] Analyse du classeur de référence → import des 19 gammes, 171 options, 306 articles
- [x] Non-régression vérifiée : 306/306 lignes de la grille résolues à l'identique
- [x] Formule de licence identifiée (somme pondérée de bits → hexadécimal)
- [ ] Correspondance bit → option à rejouer sur des licences réellement émises
- [ ] Identification de l'attribut « référence commerciale » dans Agile
- [ ] Arbitrage des 129 anomalies héritées avec l'IMI
- [ ] Interface commerciale
- [ ] Écran d'administration IMI
- [ ] Export de la fiche de configuration client
