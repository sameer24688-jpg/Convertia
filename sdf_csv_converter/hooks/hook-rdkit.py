"""
PyInstaller hook for RDKit.
Ensures all RDKit DLLs and data files are bundled.
"""
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs

# Collect everything from rdkit
datas, binaries, hiddenimports = collect_all("rdkit")

# Ensure Chem module is explicitly included
hiddenimports += [
    "rdkit.Chem",
    "rdkit.Chem.AllChem",
    "rdkit.Chem.Descriptors",
    "rdkit.Chem.Crippen",
    "rdkit.Chem.Lipinski",
    "rdkit.Chem.rdMolDescriptors",
    "rdkit.Chem.rdmolops",
    "rdkit.RDLogger",
]