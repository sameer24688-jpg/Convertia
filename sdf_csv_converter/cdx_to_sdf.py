"""
CDX/CDXML → SDF converter.

Parses CDX/CDXML files, extracts structures with all labels (titles, atom labels,
annotations, ChemProp values), and writes SDF with metadata as data tags.

Data tags:
- Metadata: XmlIndex (stable order), CompoundID, AtomLabels, Annotations.
- RDKit-computed descriptors under standard names (MolecularWeight, ...).
- ChemDraw-sourced ChemProp values under a ``ChemDraw_`` prefix, so they never
  overwrite the RDKit-computed tags.

Supports:
- CDXML (.cdxml): Direct XML parsing
- CDX (.cdx): Binary → CDXML via OpenBabel
- Streaming for large files; records are written in document order
  (single-threaded parse).
"""
import logging
from typing import Dict

from tqdm import tqdm

from rdkit import Chem
from rdkit.Chem import SDWriter

from . import cdx_parser
from . import molecule_processor as mp
from . import stream_utils as su

logger = logging.getLogger(__name__)


def convert_cdx_to_sdf(
    input_path: str,
    output_path: str,
    workers: int = 0,
    generate_3d: bool = False,
    use_v3000: bool = False,
    no_properties: bool = False,
    max_structures: int = 0,
) -> Dict[str, int]:
    """
    Convert a CDX/CDXML file to SDF.

    Args:
        input_path: Path to .cdx or .cdxml file
        output_path: Path to output .sdf file
        workers: Accepted for CLI/API compatibility but IGNORED. CDX/CDXML
            parsing is single-threaded to preserve document order.
        generate_3d: Generate 3D coordinates
        use_v3000: Write SDF in V3000 format
        no_properties: Skip RDKit property computation
        max_structures: Max structures to convert (0 = all)

    Returns:
        Dict with stats: {'total': N, 'success': N, 'failed': N}
    """
    del workers  # intentionally unused; parsing stays ordered/single-threaded
    stats = {"total": 0, "success": 0, "failed": 0}

    writer = SDWriter(output_path)
    if use_v3000:
        writer.SetForceV3000(True)

    try:
        with tqdm(desc="CDX → SDF", unit="mol") as pbar:
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
                    mol = structure.mol

                    # Set molecule title
                    title = structure.title or structure.smiles or "Unnamed"
                    mol.SetProp("_Name", title)

                    # Compute RDKit properties
                    if not no_properties:
                        computed = mp.compute_properties(mol, generate_3d=generate_3d)
                        for prop_name, prop_value in computed.items():
                            mol.SetProp(prop_name, prop_value)

                    # Add CDX-specific metadata as SDF data tags
                    cdx_props = cdx_parser.structure_to_properties_dict(structure)
                    for prop_name, prop_value in cdx_props.items():
                        if prop_value:
                            mol.SetProp(prop_name, prop_value)

                    writer.write(mol)
                    stats["success"] += 1

                except Exception as e:
                    logger.warning(
                        f"Fragment {structure.fragment_id}: error writing SDF: {e}"
                    )
                    stats["failed"] += 1

                pbar.update(1)

    finally:
        writer.close()

    logger.info(
        f"CDX → SDF complete: {stats['success']} written, "
        f"{stats['failed']} failed, {stats['total']} total"
    )
    return stats