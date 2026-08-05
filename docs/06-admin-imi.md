# Espace IMI (administration)

> Toutes les gammes sont éditables, y compris les mots/bits de licence de HDR et SATCORE.
> Pas de création de gamme, pas d'édition de la licence CRT (codée en dur, pas en base).
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
| Grille (créer/modifier/supprimer une ligne) | Modification d'une règle existante (recréer) |
| Règles de compatibilité (créer/supprimer) | Licence CRT (codée en dur, voir plus bas) |
| Mots/bits de licence HDR et SATCORE | |

Deux champs sont volontairement figés après création : `OptionGroup.code` et
`Option.caption`. Le second est la clé qui relie une option à sa colonne de grille
(`resolver.signature_of` — voir `docs/04-regles-du-classeur.md` § 3) : le renommer sans
retoucher toute la grille casse silencieusement la résolution, exactement le problème
documenté pour le classeur Excel lui-même. Le libellé commercial (`Option.label`), lui,
s'édite librement — c'est le point réellement demandé (vocabulaire technique du classeur,
ex. `CRT_options_panneau`, cf. README).

### Licences (mots/bits)

HDR et SATCORE stockent leur licence en base (`LicenseWord`/`LicenseBit`, la même somme
pondérée que documentée dans `docs/04-regles-du-classeur.md` § 4) : l'onglet « Licences »
de l'écran gamme permet d'y créer/modifier/supprimer un mot et ses bits. Chaque bit a un
« mode » exclusif :

- **piloté par une ou plusieurs options** (OU entre elles, ex. « Viterbi ou Stacked
  Viterbi ») ;
- **constante figée** (VRAI ou FAUX, indépendante de la configuration — la plupart des
  bits SATCORE) ;
- **non calculable**, avec une raison à expliquer (ex. dépend d'un compteur numérique non
  modélisé) plutôt que d'être compté silencieusement à 0.

**CRT (FEP) n'est pas éditable ici** : sa licence est calculée directement dans
`resolver.build_fep_license`, pas via des `LicenseWord`/`LicenseBit` en base — c'est une
table de fonctions et de compteurs matériels, pas une somme pondérée comme HDR/SATCORE
(voir `docs/04-regles-du-classeur.md` § 4). Créer un mot de licence pour CRT dans cet écran
est refusé côté API (422) : il ne serait jamais lu.

**Vérifié empiriquement (recherche Snowflake) qu'il n'y a rien à synchroniser depuis
Agile** pour les valeurs de licence : Agile connaît les numéros de dongle en tant
qu'articles catalogue (`S157786`/`S157787` pour CRT, déjà utilisés dans
`build_fep_license`), mais pas la clé calculée elle-même — elle dépend de la configuration
précise commandée, pas d'un attribut fixe d'un article.

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
