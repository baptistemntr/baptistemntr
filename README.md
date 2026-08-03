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

```bash
python3 tools/inspect_excel.py "data/Catalogue industriel.xlsm" > docs/analyse-classeur.md
```

## État d'avancement

- [x] Cadrage fonctionnel documenté
- [x] Connexion Snowflake (patron repris de l'agent Agile)
- [x] Modèle de données et moteur de résolution
- [x] Outils de reprise du classeur
- [ ] Analyse du classeur de référence → import des gammes et de la grille
- [ ] Identification de l'attribut « référence commerciale » dans Agile
- [ ] Rétro-ingénierie de la formule de clé de licence
- [ ] Interface commerciale
- [ ] Écran d'administration IMI
- [ ] Export de la fiche de configuration client
