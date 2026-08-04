# Règles du classeur — rétro-ingénierie

> Ce document décrit **ce que fait réellement le classeur**, établi en lisant son VBA et
> ses onglets, pas ce qu'on suppose qu'il fait. C'est la référence à opposer à toute
> évolution : la contrainte de non-régression se vérifie contre ces règles.
>
> Source : `D12424120 – Catalogue Industriel Pôle Equipements.xlsm`, écrit par Tristan
> Goldman à partir de 2019. 49 onglets, 21 gammes, 325 contrôles, 2 728 lignes de VBA.

## 1. Où vit la logique

Elle n'est **pas** dans les formules. Les onglets de gamme n'en contiennent presque pas
(24 cellules pour CRT, dont 20 renvois). Tout se joue à trois endroits :

| Emplacement | Rôle |
|---|---|
| Contrôles ActiveX de l'onglet de gamme | Les choix du commercial |
| `Main_module.Recherche_Code_Article` (VBA) | La résolution configuration → article |
| Onglet « Base de données \<Gamme\> » | La grille : quel article pour quelle combinaison |

Conséquence directe : **une lecture du classeur avec openpyxl seul ne voit rien de
l'essentiel**. Les libellés des options sont stockés dans des flux binaires MSForms, que
`tools/extract_controls.py` décode.

## 2. La convention des onglets « Base de données »

Vérifiée sur les 21 gammes, sans exception :

| Ligne / colonne | Contenu |
|---|---|
| ligne 1 | Titre de section (« Configuration PCC », « Type de châssis ») |
| ligne 2 | **Commentaire** : définition technique de l'option |
| ligne 3 | Code article du composant apporté par l'option |
| ligne 4 | Prix standard de l'option |
| ligne 5 | En-têtes — A `Produit`, B `Désignation`, C `Référence commerciale`, puis une colonne par option à partir de D |
| colonne « PRS » | Fin des options ; porte le prix standard de chaque article |
| lignes 6 et suivantes | Un article par ligne ; une croix marque chaque option embarquée |

La **ligne 2 est la réponse au reproche de vocabulaire trop technique** : la traduction de
`C0` en « PCC Motherboard + ANA board » existe déjà dans le classeur, elle n'est simplement
jamais montrée au commercial. Elle alimente désormais les infobulles.

## 3. La règle de correspondance

`Recherche_Code_Article` construit un vecteur booléen des options cochées, puis parcourt
les lignes de la grille et retient **la première dont le vecteur est strictement égal**.

```
Pour chaque colonne j : si Options_Bin(j) <> BDD_Parametres_Bin(i, j) → ligne suivante
```

Trois conséquences, souvent contre-intuitives, que le nouvel outil reproduit :

1. **L'égalité est stricte, pas une inclusion.** Une configuration à laquelle il manque une
   option ne « retombe » pas sur un article plus simple ; une configuration qui en ajoute
   une ne retombe pas non plus sur l'article de base. Dans les deux cas, le classeur répond
   `Doesn't exist` / `See Manufacturing`.
2. **La jointure se fait sur le libellé affiché** (`Caption` du contrôle = en-tête de
   colonne). Renommer un libellé casse silencieusement la grille.
3. **La première ligne trouvée gagne.** Deux lignes de même combinaison existent : la
   seconde est inatteignable, sans aucun avertissement.

### Prix

Si l'article existe et que sa colonne `PRS` est renseignée, c'est son prix standard.
Sinon, `Recherche_prix` additionne les prix (ligne 4) des options retenues et renvoie une
estimation — et refuse d'estimer dès qu'une option retenue n'a pas de prix.

## 4. Les licences

Trois gammes en produisent : **CRT** (dongle FEP), **HDR**, **SATCORE**. Le calcul est
une **somme pondérée de bits rendue en hexadécimal**, ce que l'onglet « Licences HDR »
écrit ainsi :

```
=DEC2HEX(SUMIF(valeurs; VRAI; poids))     avec poids = 1, 2, 4, 8, … (D5:D34)
```

HDR produit trois mots distincts, pas un seul :

| Mot | Portée | Bits |
|---|---|---|
| `DEM1`…`DEM6` | Un par démodulateur, recopié selon `HDR_Demod_number` | 30 (D0–D29) |
| `DEMLI` | Licence globale | 14 (D0–D13) |
| `MODLI` | Modulateur, nul si aucune unité de modulation | 17 (D0–D16) |

S'y ajoutent des champs numériques (débit min/max par démodulateur, `SR_Max`, nombre de
MODCODs) qui ne sont pas des bits.

Le FEP suit un schéma différent : des identifiants de fonction (`Licence FEP!A5:A15`) et
des compteurs encodés en hexadécimal sur deux chiffres — `n` bits bas à 1 pour `n` unités
(`TPP`, `SPP`, `IFS` : 6 max ; `UTP`, `ECP` : 2 max).

**HDR est peuplé** (`tools/import_licenses.py`, mots DEM/DEMLI/MODLI, 61 bits). 48 bits sur
61 sont calculés directement depuis une option (ou un OU entre plusieurs options — le seul
opérateur combinant plusieurs options sur un même bit dans le classeur). Les 13 restants
sont signalés plutôt que silencieusement comptés à 0 :

- **11 bits dépendent d'un compteur numérique** non représenté dans le modèle actuel
  (nombre de MODCODs, nombre d'unités de modulation, nombre de sorties IF) ou d'une
  combinaison OU/ET impliquant un tel compteur — ces champs sont des saisies libres sur
  l'écran HDR, pas des choix parmi des options discrètes ;
- **2 bits référencent des contrôles absents du catalogue chargé** : `HDR_Advanced_DEAF`
  n'a aucun libellé dans le classeur (donc jamais importé), et `HDR_RANGING_RANGING_DVBS2`
  a le même libellé (« Ranging ») qu'une colonne de la grille articles, ce qui l'exclut
  silencieusement de l'extraction — anomalie d'import à corriger séparément.

**CRT (FEP) et SATCORE restent à faire** : mécanismes structurellement différents
(comptages de fonctions pour FEP, constantes fixes mêlées à des options pour SATCORE),
pas de simple somme pondérée de bits comme HDR. Leur panneau de licence reste vide plutôt
que d'afficher une clé fausse.

> **Reste à confirmer avec l'IMI** : la correspondance bit → option d'HDR n'a pas encore
> été rejouée sur une licence réellement émise pour une validation de bout en bout.

## 5. Ce que le classeur porte au-delà de la grille

Tous les contrôles ne servent pas à trouver l'article. Trois familles cohabitent :

- **options de grille** — elles déterminent la référence à commander ;
- **options de licence** — reliées par `linkedCell` aux onglets `Licence…` / `Hardware` ;
- **attributs commerciaux** — durée de licence, mode de livraison, choix neutres « None »
  des groupes exclusifs.

Les deux dernières ne changent pas l'article mais figurent au récapitulatif : les faire
disparaître serait une régression.

Enfin, `Specific_request_checkbox`, présent sur chaque écran, n'est pas une option : il
déclenche l'avertissement de `Buttons_module.Specific_request_warning` à l'export.

## 6. Ce qui est cassé aujourd'hui

`tools/import_workbook.py` produit `docs/05-diagnostic-classeur.md`. Au moment de la
reprise : **129 anomalies**, dont

- **83 articles inatteignables** — ils exigent une colonne qu'aucun contrôle ne peut
  cocher (`ECL Single ended`, `Transpo 2400`… côté HDR). Aucune configuration ne peut les
  faire sortir ;
- **16 combinaisons en double** — seul le premier article de chaque doublon est atteignable ;
- **7 colonnes sans contrôle** et **2 colonnes techniques** (`Colonne1`, `Colonne2`,
  artefacts de mise en tableau Excel).

Ces points ne sont **pas corrigés d'office** : le classeur fait autorité tant que l'IMI n'a
pas tranché. Ils sont signalés, et le comportement actuel est reproduit à l'identique.

## 7. Vérification de non-régression

`backend/tests/test_workbook_parity.py` rejoue **les 306 lignes de la grille** comme si un
commercial avait coché exactement leurs options.

Résultat : **306/306 résolues**, dont 291 rendent leur propre article et 15 rendent le
premier article de leur combinaison en double — exactement ce que fait le classeur.
