# Espace IMI (administration)

> Toutes les gammes sont éditables. Pas de licences (mots/bits), pas de création de gamme.
> Voir `docs/02-architecture.md` § 2 pour la place de cet espace dans l'architecture
> générale.

## Historique : validé d'abord sur une gamme pilote

L'IMI éditait jusqu'ici la configuration via le classeur Excel (croix dans l'onglet
« Base de données <Gamme> », VBA). L'espace `/admin.html` la remplace par des écrans web.
Le modèle d'édition (backend `admin.py`, jamais spécifique à une gamme) a d'abord été
validé sur DTR (3 articles, pas de licence — un risque faible en cas d'erreur) avant
d'ouvrir le sélecteur de gamme à toutes les autres : casser la grille de DTR se corrige en
minutes, casser celle de HDR (141 articles, licences) en pleine période commerciale
beaucoup moins vite. Le sélecteur de gamme (`frontend/js/admin.js`, `renderFamilyPicker`)
liste désormais les 19 gammes, dans le même ordre que l'espace commercial.

## Ce qui est éditable, et ce qui ne l'est pas

| Éditable | Non éditable |
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

Les gammes à licence (CRT, HDR, SATCORE) restent éditables pour tout le reste (groupes,
options, grille, règles) : un bandeau d'avertissement le rappelle simplement dans l'écran
(`#license-notice`).

## Authentification

Mot de passe unique partagé (`ADMIN_PASSWORD` dans `backend/.env`), envoyé dans un en-tête
maison (`X-Admin-Password`) plutôt qu'`Authorization: Basic` — ce dernier fait entrer en
jeu la gestion native des identifiants du navigateur (cache par origine, ré-essai
automatique) dès qu'un 401 survient, ce qui est entré en conflit avec le formulaire de
connexion JS lors des tests (un mauvais mot de passe suivi du bon restait bloqué). Pas de
gestion d'utilisateurs ni de session persistée : le mot de passe ne vit qu'en mémoire de
l'onglet (`frontend/js/admin-api.js`), à ressaisir à chaque rechargement de page. Sans
`ADMIN_PASSWORD` configuré, toute requête vers `/api/admin/*` échoue en 503 plutôt que de
s'ouvrir sans protection. `GET /api/admin/families` sert à la fois le sélecteur de gamme
et la vérification du mot de passe au login (pas d'endpoint de connexion dédié).

## Utilisation

1. `backend/.env` : renseigner `ADMIN_PASSWORD`.
2. Démarrer le serveur normalement (`uvicorn catalogue.server:app`).
3. Ouvrir `/admin.html` (lien « Espace IMI » depuis l'espace commercial), saisir le mot de
   passe, choisir une gamme dans le sélecteur.
4. Chaque section (gamme, groupes/options, grille, règles) a son propre formulaire de
   sauvegarde ; toute modification recharge l'écran depuis l'API pour rester le reflet
   exact de la base.

## Prochaines étapes

- Édition des mots de licence (HDR, CRT, SATCORE) — hors périmètre, structure de données
  différente pour chacune (voir `docs/04-regles-du-classeur.md` § 4).
- Création de gamme complète (aujourd'hui : uniquement via `tools/import_workbook.py`).
