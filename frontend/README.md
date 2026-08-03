# Interface commerciale

HTML/CSS/JS pur, sans build ni dépendance — un dossier statique déployable tel quel
(voir `docs/02-architecture.md`).

## Lancer en local

Le backend doit tourner (voir `backend/README` du dépôt racine), puis servir ce dossier
avec n'importe quel serveur statique, par exemple :

```bash
cd frontend
python3 -m http.server 5500
```

Ouvrir http://localhost:5500. Si l'API n'écoute pas sur `http://localhost:8010`, définir
`window.CATALOGUE_API_BASE` avant le chargement de `js/api.js` (dans `index.html`).

## Ce qui est fait (V1)

- Choix de la gamme, configuration guidée par sections (reprises des titres du classeur).
- Récapitulatif fixe en haut d'écran : désignation, référence commerciale, code article
  Agile, prix — jamais masqué pendant la configuration.
- Infobulles sur chaque option (bouton `i`), reprenant le commentaire technique du
  classeur (ligne 2 des onglets « Base de données »).
- Combinaisons les plus proches affichées quand aucun article ne correspond exactement.
- Clé(s) de licence affichée(s) pour les gammes concernées (CRT, HDR, SATCORE).
- Export : impression de la fiche via le bouton dédié (`window.print()`), avec une feuille
  de style d'impression qui ne garde que le récapitulatif.

## Ce qui reste

- Espace d'administration IMI (gammes, options, grille, règles) — pas commencé.
- Export à un format autre que l'impression navigateur (PDF généré côté serveur, par ex.).
