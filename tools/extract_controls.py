#!/usr/bin/env python3
"""Extrait les contrôles ActiveX (cases à cocher / boutons radio) du classeur.

Le classeur pilote la configuration par des contrôles MSForms posés sur les onglets de
gamme. Deux de leurs propriétés portent toute la logique fonctionnelle :

- le **Caption** est la clé de jointure avec les colonnes d'options de l'onglet
  « Base de données <Gamme> » : `Main_module.Recherche_Code_Article` compare
  `Shp.Object.Caption` à l'en-tête de colonne ;
- le **GroupName** porte l'exclusivité mutuelle entre boutons radio.

Ni l'un ni l'autre n'est accessible via openpyxl : ils vivent dans un flux binaire
MorphData (MS-OFORMS), que ce module décode.

    python3 tools/extract_controls.py "data/Catalogue industriel.xlsm" > data/controls.json
"""

import json
import re
import struct
import sys
import zipfile
from pathlib import Path

DISPLAY_STYLE = {1: "Text", 2: "ListBox", 3: "ComboBox", 4: "CheckBox",
                 5: "OptionButton", 6: "ToggleButton", 7: "DropButton"}

# Propriétés de taille fixe du DataBlock : (bit du PropMask, taille en octets).
# Les bits absents de cette liste portent des chaînes, stockées dans l'ExtraDataBlock.
FIXED = [(0, 4), (1, 4), (2, 4), (3, 4), (4, 1), (5, 1), (6, 1), (7, 1),
         (9, 2), (10, 4), (11, 2), (12, 2), (13, 2), (14, 2), (15, 2),
         (16, 1), (17, 1), (18, 1), (20, 1), (21, 1),
         (24, 4), (25, 4), (26, 4), (27, 2), (28, 2), (29, 2), (30, 2)]

BIT_DISPLAY_STYLE = 6
BIT_SIZE = 8
# Les trois chaînes, dans leur ordre d'apparition. GroupName est au bit 32,
# au-delà de UnusedBits2 — vérifié sur les contrôles de ce classeur.
STRING_BITS = ((22, "value"), (23, "caption"), (32, "group"))

HEADER = 16 + 2 + 2  # CLSID, versions, cbMorphData


def _align(offset: int, size: int) -> int:
    return offset + (-offset % min(size, 4))


def parse_morphdata(blob: bytes) -> dict:
    """Décode un flux MorphData : type de contrôle, valeur, libellé, groupe.

    Le DataBlock enchaîne les propriétés dans l'ordre des bits du masque ; les chaînes
    n'y figurent que par leur longueur, leur contenu suivant dans l'ExtraDataBlock.
    """
    out: dict = {}
    mask = struct.unpack_from("<Q", blob, HEADER)[0]
    off = HEADER + 8
    lengths: list[tuple[str, int, bool]] = []

    # Un seul parcours du DataBlock, bits croissants, fixes et chaînes mêlés.
    for bit, size in sorted(FIXED + [(b, 4) for b, _ in STRING_BITS]):
        if not mask >> bit & 1:
            continue
        off = _align(off, size)
        key = dict(STRING_BITS).get(bit)
        if key:
            raw = struct.unpack_from("<I", blob, off)[0]
            lengths.append((key, raw & 0x7FFFFFFF, bool(raw & 0x80000000)))
        elif bit == BIT_DISPLAY_STYLE:
            out["type"] = DISPLAY_STYLE.get(blob[off], f"?{blob[off]}")
        off += size

    off = _align(off, 4)
    if mask >> BIT_SIZE & 1:
        off += 8  # l'ExtraDataBlock commence par Size

    for key, length, compressed in lengths:
        raw = blob[off:off + length]
        out[key] = raw.decode("latin1") if compressed else raw.decode("utf-16-le", "replace")
        off = _align(off + length, 4)

    return out


def extract(workbook: Path) -> dict:
    """Renvoie {nom d'onglet: [contrôles]} pour les onglets porteurs de contrôles."""
    with zipfile.ZipFile(workbook) as zf:
        names = set(zf.namelist())

        def read(name: str) -> str:
            return zf.read(name).decode("utf-8")

        rels = dict(re.findall(r'Id="([^"]+)"[^>]*Target="(worksheets/[^"]+)"',
                               read("xl/_rels/workbook.xml.rels")))
        titles = {rels[rid].split("/")[-1]: title
                  for title, rid in re.findall(r'<sheet name="([^"]+)"[^>]*r:id="([^"]+)"',
                                               read("xl/workbook.xml"))
                  if rid in rels}

        result: dict[str, list[dict]] = {}
        for sheet_file, title in titles.items():
            path = f"xl/worksheets/{sheet_file}"
            rels_path = f"xl/worksheets/_rels/{sheet_file}.rels"
            if path not in names or rels_path not in names:
                continue
            sheet_rels = dict(re.findall(r'Id="([^"]+)" Type="[^"]*" Target="([^"]+)"',
                                         read(rels_path)))

            controls = []
            # <mc:Fallback> répète chaque contrôle : on ne lit que <mc:Choice>.
            for block in re.findall(r'<mc:Choice Requires="x14">(.*?)</mc:Choice>',
                                    read(path), re.S):
                m = re.search(r'<control shapeId="\d+" r:id="([^"]+)" name="([^"]+)"', block)
                if not m:
                    continue
                rid, name = m.groups()
                target = sheet_rels.get(rid, "")
                if "activeX" not in target:
                    continue
                ax = "xl/" + target.replace("../", "")
                folder, filename = ax.rsplit("/", 1)
                ax_rels = f"{folder}/_rels/{filename}.rels"
                if ax_rels not in names:
                    continue
                bin_match = re.search(r'Target="([^"]+\.bin)"', read(ax_rels))
                if not bin_match:
                    continue
                info = parse_morphdata(zf.read(f"{folder}/{bin_match.group(1)}"))
                linked = re.search(r'linkedCell="([^"]+)"', block)
                info["name"] = name
                info["linked_cell"] = linked.group(1) if linked else None
                controls.append(info)

            if controls:
                result[title] = controls

    return result


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    json.dump(extract(Path(sys.argv[1])), sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
