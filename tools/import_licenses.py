#!/usr/bin/env python3
"""Construit les mots de licence à partir du classeur.

Contrairement à la grille articles (`import_workbook.py`), la formule de licence n'est pas
générique d'une gamme à l'autre : chaque onglet « Licences <Gamme> » a sa propre logique,
tracée ici à la main depuis les formules Excel (voir docs/04-regles-du-classeur.md § 4).
HDR et SATCORE sont couverts ici (mots en somme pondérée de bits). CRT (FEP) suit un
schéma entièrement différent (table de fonctions + compteurs, pas de somme) — codé
directement dans `resolver.build_fep_license`, pas dans ce fichier.

Chaque bit référence un contrôle de l'écran de la gamme par son nom technique
(`control_name`), et non par son libellé : c'est la clé stable qui survit à un renommage
d'affichage. Un bit sans référence (compteur numérique non modélisé, ex. nombre de
MODCODs) porte une raison explicite plutôt que d'être compté silencieusement comme 0 sans
justification.

    python3 tools/import_licenses.py --sortie data/licenses.json
"""

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Bit:
    """Un bit d'un mot de licence.

    `controls` : contrôle(s) dont dépend ce bit (OR si plusieurs — le classeur ne combine
    jamais autrement). `constant` : pour les bits que le classeur fixe en dur, sans aucun
    contrôle (ex. `Licences SATCORE!E5` = littéralement `VRAI`, une base toujours incluse) —
    prime sur `controls`, qui doit alors rester vide. Ni l'un ni l'autre : `unmapped_reason`
    est requis.
    """

    label: str
    source_cell: str
    controls: list[str] = field(default_factory=list)
    unmapped_reason: str | None = None
    constant: bool | None = None


def word(code: str, label: str, bits: list[Bit]) -> dict:
    return {
        "code": code,
        "label": label,
        "bits": [
            {
                "position": i,
                "weight": 2**i,
                "label": b.label,
                "source_cell": b.source_cell,
                "controls": b.controls,
                "unmapped_reason": b.unmapped_reason,
                "constant": b.constant,
            }
            for i, b in enumerate(bits)
        ],
    }


# --- HDR — mot DEM (identique pour DEM1..DEM6, un par démodulateur actif) --------------
# DEM2..DEM6 ne font que recopier DEM1 selon le nombre de démodulateurs installés
# (`=IF(HDR_Demod_number>=2,$E4,0)`...) : un seul mot suffit à représenter le contenu, le
# nombre de répétitions est une question de quantité de matériel, pas de licence propre.
DEM_BITS = [
    Bit("Viterbi", "Licences HDR!E5", ["HDR_Demod_Viterbi"]),
    Bit("4D-TCM", "Licences HDR!E6", ["HDR_Demod_4D_TCm"]),
    Bit("CADU CCSDS/ECSS/DVB-S", "Licences HDR!E7",
        ["HDR_CADU_CCSDS", "HDR_CADU_ECSS", "HDR_CADU_DVB_S"]),
    Bit("LDPC 7/8", "Licences HDR!E8", ["HDR_CADU_LDPC_78"]),
    Bit("Storage", "Licences HDR!E9", ["HDR_FEP_Storage"]),
    Bit("TCP-IP output", "Licences HDR!E10", ["HDR_FEP_TCP_IP"]),
    Bit("FIR", "Licences HDR!E11", ["HDR_Demod_FIR"]),
    Bit("DEAF", "Licences HDR!E12", ["HDR_Demod_DEAF"]),
    Bit("Cable compensation", "Licences HDR!E13", ["HDR_Demod_Cable_compensation"]),
    Bit("Stacked Viterbi", "Licences HDR!E14", ["HDR_Demod_Stacked_Viterbi"]),
    Bit("2nd IF input", "Licences HDR!E15", ["HDR_Demod_2nd_IF"]),
    Bit("1200 Mhz IF", "Licences HDR!E16", ["HDR_Demod_1200"]),
    Bit("Playback", "Licences HDR!E17", ["HDR_FEP_Payback"]),
    Bit("Niveau de modulation (bit bas)", "Licences HDR!E18", unmapped_reason=(
        "Encodage de priorité entre 16QAM/32APSK/64APSK (plus prioritaire l'emporte) : "
        "pas réductible à un simple OU, ces cases ne sont pas mutuellement exclusives "
        "dans l'écran. Nécessite une règle dédiée, pas encore écrite."
    )),
    Bit("Niveau de modulation (bit haut)", "Licences HDR!E19", unmapped_reason=(
        "Même limitation que le bit précédent (poids inférieur)."
    )),
    Bit("Turbo", "Licences HDR!E20", ["HDR_CADU_Turbo"]),
    Bit("DVB-S2", "Licences HDR!E21", ["HDR_Advanced_DVB_S2"]),
    Bit("SCCC", "Licences HDR!E22", ["HDR_Advanced_SCCC"]),
    Bit("LDPC AR4JA", "Licences HDR!E23", ["HDR_CADU_LDPC_AR4JA"]),
    Bit("Packet extraction", "Licences HDR!E24", ["HDR_FEP_Packet_extraction"]),
    Bit("VCM", "Licences HDR!E25", ["HDR_Advanced_VCM"]),
    Bit("S band input", "Licences HDR!E26", ["HDR_Demod_S_Band"]),
    Bit("X-DEAF", "Licences HDR!E27", ["HDR_Demod_X_DEAF"]),
    Bit("Combining", "Licences HDR!E28", ["HDR_Demod_Combi"]),
    Bit("Combining", "Licences HDR!E29", ["HDR_Demod_Combi"]),
    Bit("6D-TCM DSNG", "Licences HDR!E30", ["HDR_Demod_6D_TCM_DSNG"]),
    Bit("6D-TCM", "Licences HDR!E31", ["HDR_Demod_6D_TCM"]),
    Bit("1500 Mhz IF", "Licences HDR!E32", ["HDR_Demod_1500"]),
    Bit("DVB-S2-X", "Licences HDR!E33", ["HDR_Demod_DVB_S2_X"]),
    Bit("SCCC-X", "Licences HDR!E34", ["HDR_Advanced_SCCCX"]),
]

# --- HDR — mot DEMLI (licence globale) --------------------------------------------------
DEMLI_BITS = [
    Bit("WBR mode", "Licences HDR!O4", ["HDR_WBR_mode"]),
    *[
        Bit(f"Nombre de MODCODs (bit {i})", f"Licences HDR!O{5+i}", unmapped_reason=(
            "Encode le nombre de MODCODs (Licence!B73, champ numérique) en binaire sur "
            "6 bits — ce n'est pas une option cochée, ce champ n'existe pas encore dans "
            "le modèle (seuls des choix discrets sont représentés pour l'instant)."
        ))
        for i in range(6)
    ],
    Bit("DEAF & X-DEAF", "Licences HDR!O11", ["HDR_Advanced_DEAF"]),
    Bit("GSE support for DVBS2", "Licences HDR!O12", ["HDR_RANGING_GSE_DVBS2"]),
    Bit("IP over CCSDS support", "Licences HDR!O13", ["HDR_RANGING_IP_OVER_CCSDS"]),
    Bit("GFP support for DVBS2", "Licences HDR!O14", ["HDR_RANGING_GFP_DVBS2"]),
    Bit("GSE Ethernet support for DVBS2", "Licences HDR!O15", ["HDR_RANGING_GSE_ETHERNET_DVBS2"]),
    Bit("Ranging support for DVBS2", "Licences HDR!O16", ["HDR_RANGING_RANGING_DVBS2"]),
    Bit("WBR Ka 1500 mode", "Licences HDR!O17", ["HDR_WBR_Ka_mode"]),
]

# --- HDR — mot MODLI (modulateur) -------------------------------------------------------
MODLI_BITS = [
    Bit("Plusieurs unités de modulation", "Licences HDR!T3", unmapped_reason=(
        "HDR_Modulating_Unit_Number > 1 : compteur numérique de quantité, pas une option."
    )),
    Bit("2 sorties IF", "Licences HDR!T4", unmapped_reason=(
        "HDR_IF_Output_Number = 2 : compteur numérique de quantité, pas une option."
    )),
    Bit("Noise generation", "Licences HDR!T5", ["HDR_Test_Noise"]),
    Bit("FIR filtering", "Licences HDR!T6", ["HDR_Test_FIR"]),
    Bit("X-pol & channel simulation", "Licences HDR!T7", ["HDR_Test_X_Pol"]),
    Bit("Viterbi ou Stacked Viterbi", "Licences HDR!T8",
        ["HDR_Demod_Viterbi", "HDR_Demod_Stacked_Viterbi"]),
    Bit("4D/6D-TCM", "Licences HDR!T9",
        ["HDR_Demod_4D_TCm", "HDR_Demod_6D_TCM", "HDR_Demod_6D_TCM_DSNG"]),
    Bit("6D-TCM ou CADU", "Licences HDR!T10",
        ["HDR_Demod_6D_TCM", "HDR_Demod_6D_TCM_DSNG",
         "HDR_CADU_CCSDS", "HDR_CADU_ECSS", "HDR_CADU_DVB_S"]),
    Bit("LDPC 7/8", "Licences HDR!T11", ["HDR_CADU_LDPC_78"]),
    Bit("LDPC AR4JA", "Licences HDR!T12", ["HDR_CADU_LDPC_AR4JA"]),
    Bit("Turbo", "Licences HDR!T13", ["HDR_CADU_Turbo"]),
    Bit("DVB-S2", "Licences HDR!T14", ["HDR_Advanced_DVB_S2"]),
    Bit("SCCC", "Licences HDR!T15", ["HDR_Advanced_SCCC"]),
    Bit("DVB-S2-X", "Licences HDR!T16", ["HDR_Demod_DVB_S2_X"]),
    Bit("SCCC-X", "Licences HDR!T17", ["HDR_Advanced_SCCCX"]),
    Bit("S band output", "Licences HDR!T18", unmapped_reason=(
        "Licence!B61 = ET(sorties IF > 0 ; S band input) : combine un compteur numérique "
        "et une option par ET, pas encore représentable (seul le OU entre options l'est)."
    )),
    Bit("Constellation impairments", "Licences HDR!T19", ["HDR_Test_Mod_Impairements"]),
]

# --- SATCORE — mot DEM (démodulateur, DEM1 seulement — DEM2..DEM6 recopient DEM1 selon le
# nombre de démodulateurs installés, comme les DEM d'HDR : même non-couverture, quantité de
# matériel plutôt que contenu de licence) -----------------------------------------------
#
# Contrairement à HDR, la plupart des bits de ce mot ne dépendent **d'aucun contrôle** :
# `Licences SATCORE!E5:E33` les fixe en dur (`VRAI`/`FAUX` littéraux, pas des formules) —
# une base de fonctionnalités toujours incluse, indépendante de la configuration. Seuls
# trois bits (D16, D20, D21) sont pilotés par une case de l'écran SATCORE ; quatre autres
# (D23, D24, D25, D26) référencent des constantes (`D45`, `D46`, `D48`) qui, comme
# `HDR_Advanced_DEAF`, n'ont aucun contrôle pour les activer — signalées plutôt que
# silencieusement comptées à 0. Le classeur ne nomme que les bits qui ont un contrôle ou
# une constante nommée ; les autres n'ont pas de libellé au-delà de leur position (`Dn`).
SATCORE_DEM_BITS = [
    Bit("D0", "Licences SATCORE!E5", constant=True),
    Bit("D1", "Licences SATCORE!E6", constant=True),
    Bit("D2", "Licences SATCORE!E7", constant=True),
    Bit("D3", "Licences SATCORE!E8", constant=True),
    Bit("D4", "Licences SATCORE!E9", constant=True),
    Bit("D5", "Licences SATCORE!E10", constant=True),
    Bit("D6", "Licences SATCORE!E11", constant=True),
    Bit("D7", "Licences SATCORE!E12", constant=True),
    Bit("D8", "Licences SATCORE!E13", constant=True),
    Bit("D9", "Licences SATCORE!E14", constant=False),
    Bit("D10", "Licences SATCORE!E15", constant=True),
    Bit("D11", "Licences SATCORE!E16", constant=True),
    Bit("D12", "Licences SATCORE!E17", constant=False),
    Bit("D13", "Licences SATCORE!E18", constant=True),
    Bit("D14", "Licences SATCORE!E19", constant=True),
    Bit("D15", "Licences SATCORE!E20", constant=False),
    Bit("DVB-S2", "Licences SATCORE!E21", ["Satcore_DVBS2"]),
    Bit("D17", "Licences SATCORE!E22", constant=False),
    Bit("D18", "Licences SATCORE!E23", constant=False),
    Bit("D19", "Licences SATCORE!E24", constant=False),
    Bit("VCM (for DVB-S2)", "Licences SATCORE!E25", ["Satcore_VCM"]),
    Bit("S band input", "Licences SATCORE!E26", ["Satcore_Sband"]),
    Bit("D22", "Licences SATCORE!E27", constant=False),
    Bit("Combi", "Licences SATCORE!E28", unmapped_reason=(
        "Recopie Licences SATCORE!D48 (« Combi »), qui n'a aucun contrôle sur l'écran "
        "SATCORE pour l'activer — reste figé à FAUX dans le classeur."
    )),
    Bit("Combi", "Licences SATCORE!E29", unmapped_reason=(
        "Recopie Licences SATCORE!D48 (« Combi »), qui n'a aucun contrôle sur l'écran "
        "SATCORE pour l'activer — reste figé à FAUX dans le classeur."
    )),
    Bit("6D-TCM ou DVB-S & DSNG transport layer", "Licences SATCORE!E30", unmapped_reason=(
        "OU(Licences SATCORE!D45, D46) : ni « 6D-TCM (DSNG 5/6, IAI 8/9) » ni « DVB-S & "
        "DSNG transport layer » n'ont de contrôle sur l'écran SATCORE — restent figées à "
        "FAUX dans le classeur."
    )),
    Bit("6D-TCM (DSNG 5/6, IAI 8/9)", "Licences SATCORE!E31", unmapped_reason=(
        "Recopie Licences SATCORE!D45, qui n'a aucun contrôle sur l'écran SATCORE pour "
        "l'activer — reste figé à FAUX dans le classeur."
    )),
    Bit("D27", "Licences SATCORE!E32", constant=False),
    Bit("D28", "Licences SATCORE!E33", constant=False),
]

# --- SATCORE — mot DEMLI (licence globale) ----------------------------------------------
#
# Entièrement figé : aucun des 8 bits ne dépend d'un contrôle ni d'un compteur modélisable.
# D1 à D6 viennent de `Licences SATCORE!O18` (= 23 en dur, aucune formule ni contrôle ne
# l'alimente) converti en binaire — une clé toujours identique pour toute configuration
# SATCORE, tant que cette constante du classeur n'est pas changée par l'IMI.
SATCORE_DEMLI_BITS = [
    Bit("D0", "Licences SATCORE!O4", constant=False),
    Bit("D1", "Licences SATCORE!O5", constant=True),
    Bit("D2", "Licences SATCORE!O6", constant=True),
    Bit("D3", "Licences SATCORE!O7", constant=True),
    Bit("D4", "Licences SATCORE!O8", constant=False),
    Bit("D5", "Licences SATCORE!O9", constant=True),
    Bit("D6", "Licences SATCORE!O10", constant=False),
    Bit("D7", "Licences SATCORE!O11", constant=False),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sortie", type=Path, default=Path("data/licenses.json"))
    args = parser.parse_args()

    data = {
        "families": [
            {
                "family_code": "HDR",
                "words": [
                    word("DEM", "Licence démodulateur", DEM_BITS),
                    word("DEMLI", "Licence globale", DEMLI_BITS),
                    word("MODLI", "Licence modulateur", MODLI_BITS),
                ],
            },
            {
                "family_code": "SATCORE",
                "words": [
                    word("DEM", "Licence démodulateur", SATCORE_DEM_BITS),
                    word("DEMLI", "Licence globale", SATCORE_DEMLI_BITS),
                ],
            },
        ],
    }

    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    args.sortie.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    total_bits = sum(len(w["bits"]) for f in data["families"] for w in f["words"])
    unmapped = sum(
        1 for f in data["families"] for w in f["words"] for b in w["bits"]
        if b["unmapped_reason"]
    )
    families = ", ".join(f["family_code"] for f in data["families"])
    print(f"{len(data['families'])} gammes ({families}), {total_bits} bits au total dont "
          f"{unmapped} non calculables → {args.sortie}")


if __name__ == "__main__":
    main()
