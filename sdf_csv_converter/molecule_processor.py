"""
Property computation engine using RDKit.
Computes: SMILES, MolecularWeight, Formula, CLogP, TPSA, NumHAcceptors,
          NumHDonors, NumRotatableBonds, NumHeavyAtoms, NumStereoCenters.
All functions operate on a single RDKit Mol and return dicts.
Designed for multiprocessing — pure functions, no shared state.
"""
from typing import Dict, Optional

from rdkit import Chem
from rdkit.Chem import Descriptors, AllChem, rdMolDescriptors, rdmolops

from sdf_csv_converter.clogp import calc_clogp, format_clogp


def compute_properties(mol: Chem.Mol, generate_3d: bool = False) -> Dict[str, str]:
    """
    Compute all standard molecular properties for a single RDKit Mol.
    Returns a dict of property_name -> value (all values as strings).
    If mol is None, returns empty dict.

    Args:
        mol: RDKit Mol object (with hydrogens added temporarily if needed)
        generate_3d: If True, run ETKDG + UFF optimization

    Returns:
        Dict of property name to string value
    """
    if mol is None:
        return {}

    try:
        mol = Chem.Mol(mol)  # Make a copy to avoid mutating shared state
        mol = Chem.AddHs(mol)

        if generate_3d:
            AllChem.EmbedMolecule(mol, randomSeed=42)
            AllChem.MMFFOptimizeMolecule(mol)

        # Remove explicit hydrogens for descriptor computation (most expect no Hs)
        mol_smi = Chem.RemoveHs(mol)

        mw = Descriptors.MolWt(mol_smi)
        formula = rdMolDescriptors.CalcMolFormula(mol_smi)

        try:
            clogp = calc_clogp(mol_smi)
        except Exception:
            clogp = float("nan")

        try:
            tpsa = rdMolDescriptors.CalcTPSA(mol_smi)
        except Exception:
            tpsa = float("nan")

        hba = rdMolDescriptors.CalcNumHBA(mol_smi)
        hbd = rdMolDescriptors.CalcNumHBD(mol_smi)
        rot_bonds = rdMolDescriptors.CalcNumRotatableBonds(mol_smi)
        heavy_atoms = mol_smi.GetNumHeavyAtoms()
        stereo_centers = rdMolDescriptors.CalcNumAtomStereoCenters(mol_smi)

        return {
            "SMILES": Chem.MolToSmiles(mol_smi, canonical=True),
            "MolecularWeight": f"{mw:.3f}",
            "Formula": formula,
            "CLogP": format_clogp(clogp),
            "TPSA": f"{tpsa:.2f}" if not (isinstance(tpsa, float) and tpsa != tpsa) else "",
            "NumHAcceptors": str(hba),
            "NumHDonors": str(hbd),
            "NumRotatableBonds": str(rot_bonds),
            "NumHeavyAtoms": str(heavy_atoms),
            "NumStereoCenters": str(stereo_centers),
        }
    except Exception:
        return {}


def smiles_to_mol(smiles: str, generate_3d: bool = False) -> Optional[Chem.Mol]:
    """
    Parse a SMILES string into an RDKit Mol.
    Returns None if parsing fails.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    if generate_3d:
        try:
            mol = Chem.AddHs(mol)
            AllChem.EmbedMolecule(mol, randomSeed=42)
            AllChem.MMFFOptimizeMolecule(mol)
        except Exception:
            # 3D generation failed, return 2D
            mol = Chem.RemoveHs(mol)
    return mol