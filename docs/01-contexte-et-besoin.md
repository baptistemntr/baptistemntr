# Catalogue Industriel — Contexte et besoin

> Source : réunion de cadrage avec l'IMI (propriétaire de l'outil). Ce document est la
> référence fonctionnelle du projet. Toute décision de conception doit pouvoir s'y rattacher.

## 1. Ce qu'est l'outil aujourd'hui

Le **catalogue industriel** est un classeur Excel géré par les **IMI** et destiné aux
**commerciaux**. Il recense tous les produits en production et permet à un commercial de
configurer un produit pour un client, puis d'obtenir la référence à commander.

### Parcours actuel du commercial

1. Il ouvre l'onglet de la gamme concernée (CRT, HDR, DTR, …).
2. Il choisit une **configuration** : format (4U, 2U), panneau (3U, …), présence d'une
   *Power Video Board*, carte fibre, RSR simultanés, stockage, options de sécurité, etc.
3. Le classeur lui renvoie le triplet : **désignation**, **référence commerciale**,
   **code article Agile**.

### Ce que font les IMI derrière

- Un onglet « settings » par gamme contient tous les **codes articles Agile**, leurs
  **références commerciales** et leurs **désignations**.
- Les **compositions** (appelées « options » dans la réunion) sont définies *par les IMI*,
  pas par Agile : `C0` = carte mère PC + carte AN, `C1` = module M ana + carte AO,
  `C1 IF` = variante, etc. Agile ne sait pas exprimer cette notion.
- La correspondance configuration → article se fait par une **grille de croix** :
  une croix à l'intersection ligne/colonne désigne l'article correspondant.

### Cas particulier : les licences

Certaines gammes (HDR, DTR) ont un onglet **licence**. La clé de licence est générée
**automatiquement** à partir de deux sources :

- le **hardware** configuré,
- les **options de licence** cochées par le commercial.

Le calcul est **purement binaire** : chaque option pose un `1` ou un `0`, et la
concaténation de ces bits produit la clé. Le fonctionnement est identique d'une gamme à
l'autre.

## 2. Problèmes identifiés

| # | Problème | Conséquence |
|---|----------|-------------|
| P1 | **Maintien très coûteux** — colonnes de formules cachées, empilées depuis 2019 | Certaines colonnes ne servent plus, personne ne sait à quoi elles servent |
| P2 | **Aucun lien avec Agile** | Chaque nouveauté doit être ressaisie à la main dans le classeur |
| P3 | **Pas assez « commercial »** | `C0 = PC motherboard + AN board` n'est pas explicite pour un commercial ni pour un client |
| P4 | **Excel est une barrière** | Contenu à activer, front très bridé, peu engageant |
| P5 | **Nécessite beaucoup d'accompagnement** | Il faut systématiquement expliquer le fonctionnement aux nouveaux utilisateurs |

## 3. Attendus

### Contraintes fermes

- **Aucune régression** : le nouvel outil doit faire *au moins* autant que le classeur actuel.
  Toute l'information est jugée essentielle — rien ne doit être supprimé ou masqué.
- La **logique de configuration** reste la même (mêmes paramètres, même grille) ;
  c'est la couche de présentation et le mode d'alimentation qui changent.
- L'écran doit rester **lisible pour un commercial** : récapitulatif visible en permanence
  au-dessus de la configuration.

### Améliorations demandées

1. **Alimentation automatique depuis Agile via Snowflake** — c'est la valeur n°1 identifiée :
   supprimer la ressaisie manuelle (résout P2).
2. **Interface web moderne** à la place d'Excel (résout P4).
3. **Outil paramétrable / modulaire** : ajouter une gamme ou une option doit être une
   opération de configuration, pas de développement (résout P1).
4. **Vocabulaire explicité** : infobulles / popups sur chaque code (`C0`, `PVB`, `RSR`…)
   pour rendre les termes compréhensibles sans connaissance métier (résout P3).
5. **Récapitulatif de configuration exportable**, schématisé, envoyable au client.

### Posture du commanditaire

> « Je n'attends rien de particulier — propose des choses, on verra après. »

Le projet est **itératif** : une V1 est produite, puis retravaillée avec l'IMI.

## 4. Historique

Le classeur a été développé **à la main par Tristan en 2019**. Il existe :

- des **user guides** intégrés au classeur,
- un **document de procédure de mise à jour** (probablement obsolète),
- de nombreuses fonctions désormais inutilisées (ex. recherche de code article).

## 5. Points à confirmer

- [x] Récupérer le classeur Excel de référence.
- [ ] Identifier l'attribut Agile qui porte la **référence commerciale**. Piste en cours :
      dans l'UI Agile, le champ s'appelle **« Safran Sales Reference »**, onglet
      **« Sales - Export Control »** (ex. `CRT-1-2U` pour S128359). Recherché sans succès
      dans `AGILE_FLEX` (ATTID 1020/2208 = descriptions de lignes de BOM, pas cet
      attribut), dans `REV.TEXT01-15` (vides), et dans les tables candidates de
      définition d'attributs (`APPLIEDTO`, `OBJECT_DETAIL` : aucune n'a de colonne de
      libellé). Le nom « Export Control » suggère une donnée à accès restreint,
      possiblement absente de cette réplique Snowflake pour cette raison. Voir
      `tools/discover_agile.py`, notamment `--item-number` et `--list-attid-tables`.
      **Prochaine étape recommandée** : demander directement le numéro d'ATTID à un
      administrateur Agile (écran Admin > Classes > Attributs).
- [ ] Confirmer le critère « produit en production » côté Agile (cycle de vie),
      `Article.lifecycle` — jamais rempli par `agile_sync.py`. Trois pistes tentées sans
      succès (`tools/discover_agile.py --list-lifecycle-columns`, `--probe-lifecycle`) :
      `VERSION.LIFECYCLEPHASE` s'avère être du versionnage de pièces jointes/documents, pas
      le cycle de vie de l'article ; `REV.RELEASE_TYPE`/`OLD_RELEASE_TYPE` ressemblent à des
      `ENTRYID` mais n'existent dans `LISTENTRY` sous aucune langue ; `CHANGE.STATUSTYPE`
      (via `ITEM.LATEST_RELEASED_ECO`) donne des résultats incohérents (extensions de
      fichier) — `LISTENTRY.ENTRYID` n'est pas unique globalement, il faudrait connaître la
      bonne liste (`LISTID`/`LISTNAME`) pour filtrer correctement, ce qu'aucune table
      accessible ne documente. Même impasse méthodologique que la référence commerciale.
      **Prochaine étape recommandée** : demander directement à un administrateur Agile.
- [ ] Rétro-ingénierie exacte de la **formule de clé de licence** (ordre des bits, encodage,
      éventuel checksum) à partir de l'onglet licence.
- [ ] Périmètre de la V1 : toutes les gammes, ou une seule (HDR, car elle porte aussi les
      licences, donc le cas le plus complet) ?
