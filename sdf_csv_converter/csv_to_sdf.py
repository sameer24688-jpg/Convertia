"""
CSV → SDF converter.

Streams CSV rows, parses SMILES, computes RDKit properties (optional 3D),
and writes SDF with properties as data tags.

Supports:
- Large files via streaming (csv.DictReader + SDWriter)
- Newline unescaping (\\n → real newlines in SDF data fields)
- V2000 (default) or V3000 output format
- Optional 3D coordinate generation (ETKDG + MMFF)
- Parallel property computation via --workers
- Custom SMILES column name
"""
import csv
import logging
import sys
from typing import Dict, List, Optional

from tqdm import tqdm

from rdkit import Chem
from rdkit.Chem import AllChem, SDWriter

from . import molecule_processor as mp
from . import stream_utils as su

logger = logging.getLogger(__name__)


def convert_csv_to_sdf(
    input_path: str,
    output_path: str,
    smiles_col: str = "SMILES",
    workers: int = 0,
    generate_3d: bool = False,
    use_v3000: bool = False,
    max_scan: int = 0,
    chunk_size: int = 100,
) -> Dict[str, int]:
    """
    Convert a CSV file to SDF.

    Args:
        input_path: Path to input .csv file
        output_path: Path to output .sdf file
        smiles_col: Name of the column containing SMILES strings
        workers: Number of parallel workers (0 = auto)
        generate_3d: Generate 3D coordinates (ETKDG + MMFF)
        use_v3000: Write SDF in V3000 format
        max_scan: Max rows to convert (0 = all)
        chunk_size: Molecules per parallel chunk

    Returns:
        Dict with stats: {'total': N, 'success': N, 'failed': N}
    """
    stats = {"total": 0, "success": 0, "failed": 0}

    # Count rows for progress bar
    total = su.count_csv_rows(input_path)
    if total == 0:
        total = None

    # Read all rows first (we need to know columns)
    # But for large files, we can process in chunks
    with open(input_path, "r", encoding="utf-8-sig", newline="") as in_f:
        reader = csv.DictReader(in_f)
        if reader.fieldnames is None:
            logger.error("CSV file has no header row")
            return stats

        # Verify SMILES column exists
        if smiles_col not in reader.fieldnames:
            # Try case-insensitive match
            found = None
            for col in reader.fieldnames:
                if col.lower() == smiles_col.lower():
                    found = col
                    break
            if found:
                logger.info(
                    f"Using column '{found}' for SMILES (matched '{smiles_col}')"
                )
                smiles_col = found
            else:
                logger.error(
                    f"SMILES column '{smiles_col}' not found in CSV. "
                    f"Available columns: {reader.fieldnames}"
                )
                return stats

        # Identify non-SMILES columns that will become SDF data tags
        # Exclude standard computed properties that we'll regenerate
        standard_computed = {
            "SMILES",
            "MolecularWeight",
            "Formula",
            "CLogP",
            "TPSA",
            "NumHAcceptors",
            "NumHDonors",
            "NumRotatableBonds",
            "NumHeavyAtoms",
            "NumStereoCenters",
        }
        tag_columns = [
            col
            for col in reader.fieldnames
            if col != smiles_col and col not in standard_computed
        ]

        # Prepare SDWriter
        writer = SDWriter(output_path)
        if use_v3000:
            writer.SetForceV3000(True)

        with tqdm(total=total, desc="CSV → SDF", unit="mol") as pbar:
            for idx, row in enumerate(reader):
                if max_scan > 0 and idx >= max_scan:
                    break

                stats["total"] += 1
                smiles = row.get(smiles_col, "").strip()

                if not smiles:
                    logger.warning(f"Row {idx}: empty SMILES, skipping")
                    stats["failed"] += 1
                    pbar.update(1)
                    continue

                try:
                    # Parse SMILES
                    mol = mp.smiles_to_mol(smiles, generate_3d=generate_3d)
                    if mol is None:
                        logger.warning(
                            f"Row {idx}: failed to parse SMILES '{smiles[:50]}...'"
                        )
                        stats["failed"] += 1
                        pbar.update(1)
                        continue

                    # Sanitize
                    Chem.SanitizeMol(mol)

                    # Set molecule title (first non-empty from Title, Name, or SMILES)
                    title = row.get("Title", "") or row.get("Name", "") or smiles
                    mol.SetProp("_Name", title)

                    # Add computed properties as SDF data tags
                    computed = mp.compute_properties(mol, generate_3d=generate_3d)
                    for prop_name, prop_value in computed.items():
                        mol.SetProp(prop_name, prop_value)

                    # Add remaining CSV columns as SDF data tags (unescape newlines)
                    for col in tag_columns:
                        value = row.get(col, "")
                        if value:
                            mol.SetProp(col, su.unescape_newlines(value))

                    writer.write(mol)
                    stats["success"] += 1

                except Exception as e:
                    logger.warning(f"Row {idx}: error processing '{smiles[:50]}...': {e}")
                    stats["failed"] += 1

                pbar.update(1)

    writer.close()

    logger.info(
        f"CSV → SDF complete: {stats['success']} written, "
        f"{stats['failed']} failed, {stats['total']} total"
    )
    return stats