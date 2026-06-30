"""
Calculated lipophilicity (CLogP) via JPLogP.

JPLogP is an atom-contribution logP model (Plante & Werner, J Cheminform 2018,
10:61) ported from the CDK implementation (LGPL). It is distinct from RDKit's
Wildman-Crippen MolLogP (often labeled logP / SlogP).

BioByte/ACD CLogP used in some ChemDraw builds is proprietary and not available
here; JPLogP is the open calculated alternative.
"""
from __future__ import annotations

import math
from typing import Dict, Optional

from rdkit import Chem

from sdf_csv_converter.jplogp_weights import WEIGHTS

_ELECTRONEGATIVE = frozenset({"N", "O", "S", "F", "Cl", "Br", "I"})
_POLAR = frozenset({"O", "S", "N", "P"})


def calc_clogp(mol: Chem.Mol) -> float:
    """Return JPLogP for *mol*, or NaN if the structure is out of domain."""
    if mol is None:
        return float("nan")

    work = Chem.Mol(mol)
    work = Chem.AddHs(work)
    try:
        Chem.SanitizeMol(work)
    except Exception:
        return float("nan")

    logp = 0.0
    for atom in work.GetAtoms():
        code = _atom_type_code(work, atom)
        if code is None:
            return float("nan")
        increment = WEIGHTS.get(code)
        if increment is None:
            return float("nan")
        logp += increment
    return logp


def _atom_type_code(mol: Chem.Mol, atom: Chem.Atom) -> Optional[int]:
    charge = atom.GetFormalCharge()
    atomic_num = atom.GetAtomicNum()
    non_h_neighbors = _non_h_neighbors(atom)
    symbol = atom.GetSymbol()

    code = 100_000 * (charge + 1)
    code += atomic_num * 1_000
    code += non_h_neighbors * 100

    if symbol == "C":
        suffix = _carbon_special(atom)
    elif symbol == "N":
        suffix = _nitrogen_special(atom)
    elif symbol == "O":
        suffix = _oxygen_special(atom)
    elif symbol == "H":
        suffix = _hydrogen_special(atom)
    elif symbol == "F":
        suffix = _fluorine_special(atom)
    else:
        suffix = _default_special(atom)

    if suffix == 99:
        return None
    return code + suffix


def _non_h_neighbors(atom: Chem.Atom) -> int:
    return sum(1 for neighbor in atom.GetNeighbors() if neighbor.GetAtomicNum() != 1)


def _bond_order_numeric(bond: Chem.Bond) -> float:
    if bond.GetIsAromatic():
        return 1.0
    order = bond.GetBondType()
    if order == Chem.BondType.SINGLE:
        return 1.0
    if order == Chem.BondType.DOUBLE:
        return 2.0
    if order == Chem.BondType.TRIPLE:
        return 3.0
    return 1.0


def _is_polar(atom: Chem.Atom) -> bool:
    return atom.GetSymbol() in _POLAR


def _electron_withdrawing(atom: Chem.Atom) -> bool:
    return atom.GetSymbol() in _ELECTRONEGATIVE


def _polar_bond_array(atom: Chem.Atom) -> Dict[str, int]:
    counts = {"single": 0, "aromatic": 0, "double": 0, "triple": 0}
    for bond in atom.GetBonds():
        neighbor = bond.GetOtherAtom(atom)
        if not _is_polar(neighbor):
            continue
        if bond.GetIsAromatic():
            counts["aromatic"] += 1
        else:
            order = _bond_order_numeric(bond)
            if order == 1.0:
                counts["single"] += 1
            elif order == 2.0:
                counts["double"] += 1
            elif order == 3.0:
                counts["triple"] += 1
    return counts


def _bound_to(atom: Chem.Atom, symbol: str) -> bool:
    return any(neighbor.GetSymbol() == symbol for neighbor in atom.GetNeighbors())


def _num_more_electronegative_than_carbon(atom: Chem.Atom) -> float:
    total = 0.0
    for bond in atom.GetBonds():
        neighbor = bond.GetOtherAtom(atom)
        if _electron_withdrawing(neighbor):
            total += _bond_order_numeric(bond)
    return total


def _double_bond_hetero(atom: Chem.Atom) -> bool:
    for bond in atom.GetBonds():
        if bond.GetIsAromatic():
            continue
        neighbor = bond.GetOtherAtom(atom)
        if _is_polar(neighbor) and _bond_order_numeric(bond) == 2.0:
            return True
    return False


def _carbonyl_conjugated(atom: Chem.Atom) -> bool:
    for bond in atom.GetBonds():
        if bond.GetIsAromatic() or _bond_order_numeric(bond) != 1.0:
            continue
        neighbor = bond.GetOtherAtom(atom)
        if _double_bond_hetero(neighbor):
            return True
    return False


def _next_to_aromatic(atom: Chem.Atom) -> bool:
    if atom.GetIsAromatic():
        return False
    for bond in atom.GetBonds():
        if _bond_order_numeric(bond) != 1.0 or bond.GetIsAromatic():
            continue
        neighbor = bond.GetOtherAtom(atom)
        if neighbor.GetIsAromatic():
            return True
    return False


def _check_alpha_carbonyl(atom: Chem.Atom, symbol: str) -> bool:
    for bond in atom.GetBonds():
        neighbor = bond.GetOtherAtom(atom)
        for bond2 in neighbor.GetBonds():
            other = bond2.GetOtherAtom(neighbor)
            if other.GetSymbol() == symbol and _bond_order_numeric(bond2) == 1.0:
                return True
    return False


def _hydrogen_special(atom: Chem.Atom) -> int:
    if atom.GetDegree() == 0:
        return 0
    neighbor = atom.GetNeighbors()[0]
    num_neighbors = neighbor.GetDegree()
    if neighbor.GetAtomicNum() != 6:
        return 50
    if _carbonyl_conjugated(neighbor):
        return 51
    ox = _num_more_electronegative_than_carbon(neighbor)
    if num_neighbors == 4:
        if ox == 0.0:
            return 46
        if ox == 1.0:
            return 47
        if ox == 2.0:
            return 48
        if ox == 3.0:
            return 49
    elif num_neighbors == 3:
        if ox == 0.0:
            return 47
        if ox == 1.0:
            return 48
        if ox >= 2.0:
            return 49
    elif num_neighbors == 2:
        if ox == 0.0:
            return 48
        if ox >= 1.0:
            return 49
    elif num_neighbors == 1:
        return 121
    return 0


def _default_special(atom: Chem.Atom) -> int:
    polar = _polar_bond_array(atom)
    if atom.GetIsAromatic():
        return 10
    return (
        polar["single"]
        + polar["double"]
        + polar["triple"]
        + polar["aromatic"]
    )


def _fluorine_special(atom: Chem.Atom) -> int:
    if atom.GetDegree() != 1:
        return 99
    neighbor = atom.GetNeighbors()[0]
    neighbor_conn = neighbor.GetDegree()
    ox = _num_more_electronegative_than_carbon(neighbor)
    symbol = neighbor.GetSymbol()
    if symbol == "S":
        return 8
    if symbol == "B":
        return 9
    if symbol != "C":
        return 1
    if neighbor_conn == 2:
        return 2
    if neighbor_conn == 3:
        return 3
    if neighbor_conn == 4 and ox <= 2:
        return 5
    if neighbor_conn == 4 and ox > 2:
        return 7
    return 99


def _oxygen_special(atom: Chem.Atom) -> int:
    num_connections = atom.GetDegree()
    if num_connections == 2:
        if _bound_to(atom, "N"):
            return 1
        if _bound_to(atom, "S"):
            return 2
        if atom.GetIsAromatic():
            return 8
        return 3
    if num_connections == 1:
        if _bound_to(atom, "N"):
            return 4
        if _bound_to(atom, "S"):
            return 5
        if _check_alpha_carbonyl(atom, "O"):
            return 6
        if _check_alpha_carbonyl(atom, "N"):
            return 9
        if _check_alpha_carbonyl(atom, "S"):
            return 10
        return 7
    return 0


def _nitrogen_special(atom: Chem.Atom) -> int:
    num_connections = atom.GetDegree()
    polar = _polar_bond_array(atom)
    single_polar = polar["single"]
    if num_connections == 4:
        return 9
    if num_connections == 3:
        if _next_to_aromatic(atom):
            return 1
        if _carbonyl_conjugated(atom):
            return 2
        if _double_bond_hetero(atom):
            return 10
        if single_polar > 0:
            return 3
        return 4
    if num_connections == 2:
        if atom.GetIsAromatic():
            return 5
        if _double_bond_hetero(atom):
            return 6
        return 7
    if num_connections == 1:
        return 8
    return 0


def _carbon_special(atom: Chem.Atom) -> int:
    num_connections = atom.GetDegree()
    polar = _polar_bond_array(atom)
    single_polar = polar["single"]
    double_polar = polar["double"]
    triple_polar = polar["triple"]
    aromatic_polar = polar["aromatic"]

    if num_connections == 4:
        if single_polar > 0:
            return 3
        return 2
    if num_connections == 3:
        if atom.GetIsAromatic():
            if aromatic_polar >= 1 and single_polar == 0:
                return 11
            if aromatic_polar == 0 and single_polar == 1:
                return 5
            if aromatic_polar >= 1 and single_polar == 1:
                return 13
            return 4
        if double_polar == 1 and single_polar == 0:
            return 7
        if single_polar >= 1 and double_polar == 0:
            return 8
        if double_polar == 1 and single_polar >= 1:
            return 14
        return 6
    if num_connections == 2:
        if triple_polar == 1 and single_polar == 0:
            return 12
        if triple_polar == 0 and single_polar == 1:
            return 10
        if triple_polar == 1 and single_polar == 1:
            return 15
        return 9
    if (
        single_polar > 0
        or double_polar > 0
        or aromatic_polar > 0
        or triple_polar > 0
    ):
        return 1
    return 0


def format_clogp(value: float) -> str:
    """Format CLogP for CSV output."""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return f"{value:.3f}"
