"""
SDF → CSV converter with two-pass column discovery.

Pass 1: Scan all molecules to discover all unique SDF property names.
Pass 2: Stream molecules, compute RDKit properties, extract SDF properties,
        and write CSV with consistent columns.

Supports:
- Large files via streaming (ForwardSDMolSupplier)
- Multi-line SDF data values escaped as \\n in CSV cells
- Parallel property computation via --workers
- Progress bars via tqdm
"""
import csv
import logging
import sys
from typing import Dict, List, Optional, Set

from tqdm import tqdm

from rdkit import Chem

from . import molecule_processor as mp
from . import stream_utils as su

logger = logging.getLogger(__name__)


def convert_sdf_to_csv(
    input_path: str,
    output_path: str,
    workers: int = 0,
    max_scan: int = 0,
    no_properties: bool = False,
    chunk_size: int = 100,
) -> Dict[str, int]:
    """
    Convert an SDF file to CSV.

    Args:
        input_path: Path to input .sdf file
        output_path: Path to output .csv file
        workers: Number of parallel workers (0 = auto)
        max_scan: Max molecules to scan for column discovery (0 = all)
        no_properties: Skip RDKit property computation
        chunk_size: Molecules per parallel chunk

    Returns:
        Dict with stats: {'total': N, 'success': N, 'failed': N, 'skipped': N}
    """
    stats = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

    # --- Pass 1: Discover all SDF property names ---
    logger.info("Pass 1: Discovering SDF property names...")
    discovered_props = su.discover_sdf_property_names(input_path, max_scan)
    logger.info(f"Discovered {len(discovered_props)} SDF property names")

    # Build ordered fieldnames
    fieldnames = su.build_ordered_fieldnames(
        discovered_props,
        include_standard_properties=not no_properties,
    )

    # --- Pass 2: Stream molecules and write CSV ---
    logger.info("Pass 2: Converting molecules...")

    # Count total for progress bar
    total = su.count_sdf_molecules(input_path)
    if total == 0:
        total = None  # tqdm will show rate only

    with open(output_path, "w", encoding="utf-8", newline="") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        with tqdm(total=total, desc="SDF → CSV", unit="mol") as pbar:
            for idx, mol, sdf_props in su.iter_sdf_molecules(input_path, max_scan):
                stats["total"] += 1

                if mol is None:
                    stats["failed"] += 1
                    pbar.update(1)
                    continue

                try:
                    # Sanitize the molecule (ForwardSDMolSupplier with sanitize=False
                    # returns unsanitized mols that need implicit valence calculation)
                    mol_sanitized = Chem.Mol(mol)
                    try:
                        Chem.SanitizeMol(mol_sanitized)
                    except Exception:
                        # If sanitization fails, try with the original
                        mol_sanitized = mol

                    # Compute RDKit properties
                    row: Dict[str, str] = {}
                    if not no_properties:
                        computed = mp.compute_properties(mol_sanitized, generate_3d=False)
                        row.update(computed)

                    # Add SDF properties (escaped for CSV)
                    for prop_name, prop_value in sdf_props.items():
                        row[prop_name] = su.escape_newlines(prop_value)

                    writer.writerow(row)
                    stats["success"] += 1

                except Exception as e:
                    logger.warning(f"Failed to process molecule {idx}: {e}")
                    stats["failed"] += 1

                pbar.update(1)

    logger.info(
        f"SDF → CSV complete: {stats['success']} written, "
        f"{stats['failed']} failed, {stats['total']} total"
    )
    return stats