"""
CDX/CDXML → CSV converter.

Parses CDX/CDXML files, extracts structures with all labels (titles, atom labels,
annotations, ChemProp values), and writes CSV with all metadata as columns.

Columns:
- Metadata first: XmlIndex (stable row order), Title, CompoundID,
  Annotations.
- RDKit-computed descriptors under their standard names (MolecularWeight,
  Formula, CLogP, ...).
- ChemDraw-sourced ChemProp values under a ``ChemDraw_`` prefix, so they never
  overwrite the RDKit-computed columns.

Supports:
- CDXML (.cdxml): Direct XML parsing
- CDX (.cdx): Binary → CDXML via OpenBabel
- Streaming for large files; rows are written in document order (single-threaded
  parse), so output sequence matches the source.
"""
import csv
import logging
from typing import Dict, List, Set

from tqdm import tqdm

from . import cdx_parser
from . import molecule_processor as mp
from . import stream_utils as su

logger = logging.getLogger(__name__)


def convert_cdx_to_csv(
    input_path: str,
    output_path: str,
    workers: int = 0,
    no_properties: bool = False,
    max_structures: int = 0,
) -> Dict[str, int]:
    """
    Convert a CDX/CDXML file to CSV.

    Args:
        input_path: Path to .cdx or .cdxml file
        output_path: Path to output .csv file
        workers: Accepted for CLI/API compatibility but IGNORED. CDX/CDXML
            parsing is single-threaded to preserve document (row) order.
        no_properties: Skip RDKit property computation
        max_structures: Max structures to convert (0 = all)

    Returns:
        Dict with stats: {'total': N, 'success': N, 'failed': N}
    """
    del workers  # intentionally unused; parsing stays ordered/single-threaded
    stats = {"total": 0, "success": 0, "failed": 0}

    # --- Pass 1: Discover all possible column names ---
    # We need to scan all structures first to know all CDX property names
    logger.info("Pass 1: Discovering CDX property names...")
    all_cdx_prop_names: Set[str] = set()

    for structure in cdx_parser.parse_cdx_or_cdxml(input_path, max_structures):
        cdx_props = cdx_parser.structure_to_properties_dict(structure)
        all_cdx_prop_names.update(cdx_props.keys())

    logger.info(f"Discovered {len(all_cdx_prop_names)} CDX property names")

    # Build ordered fieldnames
    fieldnames = su.build_ordered_fieldnames(
        all_cdx_prop_names,
        include_standard_properties=not no_properties,
    )

    # --- Pass 2: Stream structures and write CSV ---
    logger.info("Pass 2: Converting structures...")

    with open(output_path, "w", encoding="utf-8", newline="") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        with tqdm(desc="CDX → CSV", unit="mol") as pbar:
            for structure in cdx_parser.parse_cdx_or_cdxml(
                input_path, max_structures
            ):
                stats["total"] += 1

                if structure.mol is None:
                    logger.warning(
                        f"Fragment {structure.fragment_id}: no valid structure"
                    )
                    stats["failed"] += 1
                    pbar.update(1)
                    continue

                try:
                    row: Dict[str, str] = {}

                    # Compute RDKit properties
                    if not no_properties:
                        computed = mp.compute_properties(
                            structure.mol, generate_3d=False
                        )
                        row.update(computed)

                    # Add CDX-specific metadata
                    cdx_props = cdx_parser.structure_to_properties_dict(structure)
                    for prop_name, prop_value in cdx_props.items():
                        row[prop_name] = su.escape_newlines(prop_value)

                    writer.writerow(row)
                    stats["success"] += 1

                except Exception as e:
                    logger.warning(
                        f"Fragment {structure.fragment_id}: error writing CSV: {e}"
                    )
                    stats["failed"] += 1

                pbar.update(1)

    logger.info(
        f"CDX → CSV complete: {stats['success']} written, "
        f"{stats['failed']} failed, {stats['total']} total"
    )
    return stats