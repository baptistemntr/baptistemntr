# Diagnostic du classeur

> Produit par `tools/import_workbook.py`. Ce document liste ce que la reprise du
> classeur ne peut pas trancher seule : chaque point est à valider avec l'IMI avant
> la bascule, la contrainte de non-régression interdisant toute correction d'office.


## Volumétrie

| Gamme | Options de grille | Autres options | Articles | Licence | Anomalies |
|-------|------------------:|---------------:|---------:|:-------:|----------:|
| CRT | 21 | 12 | 42 | oui | 0 |
| HDR | 30 | 58 | 141 | oui | 89 |
| SATCORE | 5 | 7 | 5 | oui | 2 |
| DTR | 4 | 6 | 3 | — | 0 |
| RSR-RF | 4 | 6 | 3 | — | 0 |
| RSR-FT | 7 | 3 | 6 | — | 0 |
| BSS | 6 | 6 | 6 | — | 0 |
| WBR | 9 | 0 | 4 | — | 0 |
| Nuron | 4 | 8 | 4 | — | 0 |
| RTR | 13 | 1 | 12 | — | 0 |
| Stream Ka | 30 | 8 | 13 | — | 1 |
| Stream Ka RS | 4 | 1 | 5 | — | 1 |
| Stream Ka Wide | 4 | 1 | 5 | — | 0 |
| Transpo S band | 6 | 1 | 6 | — | 2 |
| Transpo X Image | 4 | 0 | 5 | — | 1 |
| Comtrack | 7 | 1 | 30 | — | 31 |
| SSPA S band | 6 | 4 | 6 | — | 0 |
| StreamX | 6 | 4 | 9 | — | 0 |
| L200T | 1 | 12 | 1 | — | 2 |

## Articles inatteignables (83)

- **HDR** — S100683 (ligne 6) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110609 (ligne 8) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110610 (ligne 9) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110611 (ligne 10) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110612 (ligne 11) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110614 (ligne 12) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110615 (ligne 13) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110616 (ligne 14) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110617 (ligne 15) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110618 (ligne 16) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110619 (ligne 17) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110620 (ligne 18) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110621 (ligne 19) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110622 (ligne 20) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110624 (ligne 22) exige ECL Differential, jamais sélectionnable
- **HDR** — S110625 (ligne 23) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110626 (ligne 24) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S110627 (ligne 25) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110628 (ligne 26) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S110629 (ligne 27) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110630 (ligne 28) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S110631 (ligne 29) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S110632 (ligne 30) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110633 (ligne 31) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S110634 (ligne 32) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110635 (ligne 33) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S110636 (ligne 34) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110637 (ligne 35) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S110638 (ligne 36) exige ECL Single ended, jamais sélectionnable
- **HDR** — S110639 (ligne 37) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S111410 (ligne 38) exige ECL Single ended, jamais sélectionnable
- **HDR** — S111411 (ligne 39) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S111412 (ligne 40) exige ECL Single ended, jamais sélectionnable
- **HDR** — S111413 (ligne 41) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S111414 (ligne 42) exige ECL Single ended, jamais sélectionnable
- **HDR** — S111415 (ligne 43) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S111416 (ligne 44) exige ECL Single ended, jamais sélectionnable
- **HDR** — S111417 (ligne 45) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S111418 (ligne 46) exige ECL Single ended, jamais sélectionnable
- **HDR** — S111419 (ligne 47) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S111420 (ligne 48) exige ECL Single ended, jamais sélectionnable
- **HDR** — S111421 (ligne 49) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S111422 (ligne 50) exige ECL Single ended, jamais sélectionnable
- **HDR** — S111423 (ligne 51) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S111424 (ligne 52) exige ECL Single ended, jamais sélectionnable
- **HDR** — S111425 (ligne 53) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S111426 (ligne 54) exige ECL Single ended, jamais sélectionnable
- **HDR** — S111427 (ligne 55) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S111428 (ligne 56) exige ECL Single ended, jamais sélectionnable
- **HDR** — S111429 (ligne 57) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S111430 (ligne 58) exige ECL Single ended, jamais sélectionnable
- **HDR** — S111431 (ligne 59) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S111432 (ligne 60) exige ECL Single ended, jamais sélectionnable
- **HDR** — S111433 (ligne 61) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S111434 (ligne 62) exige ECL Differential, Transpo 3450, jamais sélectionnable
- **HDR** — S111435 (ligne 63) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S111436 (ligne 64) exige ECL Single ended, jamais sélectionnable
- **HDR** — S111437 (ligne 65) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S111438 (ligne 66) exige ECL Single ended, jamais sélectionnable
- **HDR** — S111452 (ligne 67) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S116152 (ligne 68) exige ECL Differential, jamais sélectionnable
- **HDR** — S116594 (ligne 69) exige ECL Single ended, jamais sélectionnable
- **HDR** — S117362 (ligne 70) exige ECL Differential, jamais sélectionnable
- **HDR** — S118063 (ligne 71) exige ECL Differential, jamais sélectionnable
- **HDR** — S118557 (ligne 74) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S119878 (ligne 75) exige ECL Differential, jamais sélectionnable
- **HDR** — S122291 (ligne 89) exige ECL Single ended, jamais sélectionnable
- **HDR** — S124152 (ligne 91) exige ECL Differential, jamais sélectionnable
- **HDR** — S125268 (ligne 93) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S125855 (ligne 94) exige ECL Single ended, jamais sélectionnable
- **HDR** — S125856 (ligne 95) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S126766 (ligne 96) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S127979 (ligne 97) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S128155 (ligne 98) exige ECL Single ended, Transpo 2400, jamais sélectionnable
- **HDR** — S129187 (ligne 99) exige ECL Single ended, jamais sélectionnable
- **HDR** — S129207 (ligne 100) exige ECL Single ended, jamais sélectionnable
- **HDR** — S129641 (ligne 103) exige ECL Single ended, jamais sélectionnable
- **HDR** — S131390 (ligne 105) exige ECL Single ended, jamais sélectionnable
- **HDR** — S131795 (ligne 106) exige ECL Single ended, jamais sélectionnable
- **HDR** — S132403 (ligne 107) exige ECL Single ended, jamais sélectionnable
- **HDR** — S134167 (ligne 108) exige ECL Differential, Transpo 2400, jamais sélectionnable
- **HDR** — S136778 (ligne 118) exige ECL Single ended, jamais sélectionnable
- **SATCORE** — S100676 (ligne 8) exige 1DEC Demod board, jamais sélectionnable

## Articles sans aucune option (19)

- **Transpo S band** — S101542 (ligne 11) ne coche aucune option : il ne sort que sur une configuration vide
- **Transpo X Image** — S101542 (ligne 10) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — SM01047790A (ligne 13) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — SM01047791A (ligne 14) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — SM01046307A (ligne 15) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — SM01059319A (ligne 16) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — S105844 (ligne 17) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — S123497 (ligne 18) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — S123498 (ligne 19) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — S123499 (ligne 20) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — S123500 (ligne 21) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — S107232 (ligne 22) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — SP01035716A (ligne 23) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — S123165 (ligne 24) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — S123167 (ligne 25) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — S123169 (ligne 26) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — S123170 (ligne 27) ne coche aucune option : il ne sort que sur une configuration vide
- **Comtrack** — S140031 (ligne 28) ne coche aucune option : il ne sort que sur une configuration vide
- **L200T** — Aucun (ligne 6) ne coche aucune option : il ne sort que sur une configuration vide

## Combinaisons en double (16)

- **HDR** — S134913 (ligne 113) a la même combinaison que S134913 (ligne 112) : seul le premier peut être retourné
- **Comtrack** — SM01047791A (ligne 14) a la même combinaison que SM01047790A (ligne 13) : seul le premier peut être retourné
- **Comtrack** — SM01046307A (ligne 15) a la même combinaison que SM01047790A (ligne 13) : seul le premier peut être retourné
- **Comtrack** — SM01059319A (ligne 16) a la même combinaison que SM01047790A (ligne 13) : seul le premier peut être retourné
- **Comtrack** — S105844 (ligne 17) a la même combinaison que SM01047790A (ligne 13) : seul le premier peut être retourné
- **Comtrack** — S123497 (ligne 18) a la même combinaison que SM01047790A (ligne 13) : seul le premier peut être retourné
- **Comtrack** — S123498 (ligne 19) a la même combinaison que SM01047790A (ligne 13) : seul le premier peut être retourné
- **Comtrack** — S123499 (ligne 20) a la même combinaison que SM01047790A (ligne 13) : seul le premier peut être retourné
- **Comtrack** — S123500 (ligne 21) a la même combinaison que SM01047790A (ligne 13) : seul le premier peut être retourné
- **Comtrack** — S107232 (ligne 22) a la même combinaison que SM01047790A (ligne 13) : seul le premier peut être retourné
- **Comtrack** — SP01035716A (ligne 23) a la même combinaison que SM01047790A (ligne 13) : seul le premier peut être retourné
- **Comtrack** — S123165 (ligne 24) a la même combinaison que SM01047790A (ligne 13) : seul le premier peut être retourné
- **Comtrack** — S123167 (ligne 25) a la même combinaison que SM01047790A (ligne 13) : seul le premier peut être retourné
- **Comtrack** — S123169 (ligne 26) a la même combinaison que SM01047790A (ligne 13) : seul le premier peut être retourné
- **Comtrack** — S123170 (ligne 27) a la même combinaison que SM01047790A (ligne 13) : seul le premier peut être retourné
- **Comtrack** — S140031 (ligne 28) a la même combinaison que SM01047790A (ligne 13) : seul le premier peut être retourné

## Colonnes que l'écran ne peut pas cocher (7)

- **HDR** — « ECL Single ended » : aucun contrôle de l'écran ne porte ce libellé, la colonne ne peut jamais être cochée
- **HDR** — « ECL Differential » : aucun contrôle de l'écran ne porte ce libellé, la colonne ne peut jamais être cochée
- **HDR** — « Transpo 2400 » : aucun contrôle de l'écran ne porte ce libellé, la colonne ne peut jamais être cochée
- **HDR** — « Transpo 3450 » : aucun contrôle de l'écran ne porte ce libellé, la colonne ne peut jamais être cochée
- **SATCORE** — « 1DEC Demod board » : aucun contrôle de l'écran ne porte ce libellé, la colonne ne peut jamais être cochée
- **Stream Ka** — « 6UP 1.2GHz2 » : aucun contrôle de l'écran ne porte ce libellé, la colonne ne peut jamais être cochée
- **Transpo S band** — « MOD Channel » : aucun contrôle de l'écran ne porte ce libellé, la colonne ne peut jamais être cochée

## Contrôles sans libellé (2)

- **HDR** — contrôle « HDR_Specific_software » sans Caption : il ne peut correspondre à aucune colonne de la grille
- **HDR** — contrôle « HDR_Advanced_DEAF » sans Caption : il ne peut correspondre à aucune colonne de la grille

## Colonnes techniques résiduelles (2)

- **Stream Ka RS** — colonne « Colonne1 » (artefact de mise en tableau Excel, sans option associée)
- **L200T** — colonne « Colonne2 » (artefact de mise en tableau Excel, sans option associée)
