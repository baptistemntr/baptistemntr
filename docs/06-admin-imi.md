# Espace IMI (administration)

> Périmètre V1 : gamme pilote (`DTR`), pas de licences, pas de création de gamme. Voir
> `docs/02-architecture.md` § 2 pour la place de cet espace dans l'architecture générale.

## Pourquoi une gamme pilote

L'IMI éditait jusqu'ici la configuration via le classeur Excel (croix dans l'onglet
« Base de données <Gamme> », VBA). L'espace `/admin.html` la remplace par des écrans web,
mais le risque n'est pas symétrique entre gammes : casser la grille de DTR (3 articles)
se corrige en quelques minutes ; casser celle de HDR (141 articles, licences) en pleine
période commerciale ne se corrige pas aussi vite. **DTR sert donc à valider le modèle
d'édition avant de l'ouvrir aux autres gammes** — le code n'est pas spécifique à DTR
(`backend/source/catalogue/admin.py` ne connaît aucun nom de gamme), seule
`frontend/js/admin.js` fixe `FAMILY_CODE = "DTR"`. Ouvrir une autre gamme, une fois DTR
validée, se fait en changeant cette seule ligne.

## Ce qui est éditable, et ce qui ne l'est pas

| Éditable | Non éditable (V1) |
|---|---|
| Libellé et description de la gamme | Création d'une nouvelle gamme |
| Groupes d'options (libellé, section, aide) | `OptionGroup.code` après création |
| Options (libellé, définition technique) | `Option.caption` après création |
| Grille (créer/modifier/supprimer une ligne) | Mots et bits de licence (DEM, DEMLI…) |
| Règles de compatibilité (créer/supprimer) | Modification d'une règle existante (recréer) |

Deux champs sont volontairement figés après création : `OptionGroup.code` et
`Option.caption`. Le second est la clé qui relie une option à sa colonne de grille
(`resolver.signature_of` — voir `docs/04-regles-du-classeur.md` § 3) : le renommer sans
retoucher toute la grille casse silencieusement la résolution, exactement le problème
documenté pour le classeur Excel lui-même. Le libellé commercial (`Option.label`), lui,
s'édite librement — c'est le point réellement demandé (vocabulaire technique du classeur,
ex. `CRT_options_panneau`, cf. README).

## Authentification

Mot de passe unique partagé (`ADMIN_PASSWORD` dans `backend/.env`), envoyé en HTTP Basic.
Pas de gestion d'utilisateurs ni de session persistée : le mot de passe ne vit qu'en
mémoire de l'onglet (`frontend/js/admin-api.js`), à ressaisir à chaque rechargement de
page. Sans `ADMIN_PASSWORD` configuré, toute requête vers `/api/admin/*` échoue en 503
plutôt que de s'ouvrir sans protection.

## Utilisation

1. `backend/.env` : renseigner `ADMIN_PASSWORD`.
2. Démarrer le serveur normalement (`uvicorn catalogue.server:app`).
3. Ouvrir `/admin.html` (lien « Espace IMI » à ajouter côté commercial si besoin, ou URL
   directe), saisir le mot de passe.
4. Chaque section (gamme, groupes/options, grille, règles) a son propre formulaire de
   sauvegarde ; toute modification recharge l'écran depuis l'API pour rester le reflet
   exact de la base.

## Prochaines étapes une fois DTR validée

- Ouvrir la sélection de gamme à toutes les gammes (retirer la restriction dans
  `frontend/js/admin.js`).
- Édition des mots de licence (HDR, CRT, SATCORE) — hors périmètre V1, structure de
  données différente pour chacune (voir `docs/04-regles-du-classeur.md` § 4).
- Création de gamme complète (aujourd'hui : uniquement via `tools/import_workbook.py`).
