"""
Streaming I/O utilities for large-scale SDF/CSV processing.

Features:
- Two-pass SDF column discovery (scan all molecules for property names before writing CSV)
- Chunked multiprocessing with Pool.imap_unordered for property computation
- tqdm progress bars with line-count totals
- Newline escaping/unescaping for multi-line SDF data in CSV cells
"""
import csv
import io
import logging
import os
import re
from itertools import islice
from multiprocessing import Pool, cpu_count
from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, Set, Tuple

from tqdm import tqdm

from rdkit import Chem

logger = logging.getLogger(__name__)

# SDF delimiter marker
SDF_DELIMITER = "$$$$"
# Multi-line newline escape sequence used in CSV cells
NEWLINE_ESCAPE = "\\n"


def count_sdf_molecules(filepath: str) -> int:
    """
    Fast count of molecules in an SDF file by counting $$$$ delimiters.
    Does NOT parse molecules — just scans lines.
    """
    count = 0
    try:
        with open(filepath, "rb") as f:
            # Use binary read with buffering for speed
            chunk = f.read(io.DEFAULT_BUFFER_SIZE)
            # Count all occurrences
            count = chunk.count(b"$$$$")
    except Exception:
        return 0
    return count


def count_csv_rows(filepath: str) -> int:
    """
    Count data rows in a CSV file (excluding header).
    """
    count = 0
    try:
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for _ in reader:
                count += 1
    except Exception:
        return 0
    return count


def estimate_line_count(filepath: str) -> int:
    """
    Estimate total lines in a file by reading a sample.
    Used for tqdm when we don't know the exact count.
    """
    try:
        size = os.path.getsize(filepath)
        with open(filepath, "rb") as f:
            sample = f.read(min(io.DEFAULT_BUFFER_SIZE * 4, size))
        avg_line_len = max(len(sample) / max(sample.count(b"\n"), 1), 1)
        return int(size / avg_line_len)
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# SDF two-pass column discovery
# ---------------------------------------------------------------------------

def discover_sdf_property_names(filepath: str, max_scan: int = 0) -> Set[str]:
    """
    First pass: scan SDF file to collect ALL unique property names.
    This ensures consistent CSV column headers even if properties appear
    only in later molecules.

    Args:
        filepath: Path to SDF file
        max_scan: If > 0, only scan first N molecules for column discovery

    Returns:
        Set of all unique property names found
    """
    property_names: Set[str] = set()
    supplier = Chem.ForwardSDMolSupplier(
        filepath, sanitize=False, removeHs=False, strictParsing=False
    )

    for i, mol in enumerate(supplier):
        if mol is None:
            continue
        if max_scan > 0 and i >= max_scan:
            break
        # Extract all property names from this molecule
        for prop_name in mol.GetPropNames(includePrivate=False, includeComputed=False):
            property_names.add(prop_name)

    # ForwardSDMolSupplier doesn't have a close method in older RDKit
    return property_names


# ---------------------------------------------------------------------------
# SDF molecule generator (streaming)
# ---------------------------------------------------------------------------


def iter_sdf_molecules(
    filepath: str,
    max_scan: int = 0,
) -> Generator[Tuple[int, Optional[Chem.Mol], Dict[str, str]], None, None]:
    """
    Streaming generator over SDF molecules.
    Yields (index, mol, properties_dict) for each molecule.
    If mol is None, the molecule failed to parse — properties will include
    raw text properties from the header but no structure.

    Properties dict excludes internal RDKit computed properties.

    Args:
        filepath: Path to SDF file
        max_scan: If > 0, stop after N molecules

    Yields:
        (molecule_index, mol_or_None, properties_dict)
    """
    supplier = Chem.ForwardSDMolSupplier(
        filepath, sanitize=False, removeHs=False, strictParsing=False
    )
    for i, mol in enumerate(supplier):
        if max_scan > 0 and i >= max_scan:
            break

        props: Dict[str, str] = {}
        if mol is not None:
            for prop_name in mol.GetPropNames(
                includePrivate=False, includeComputed=False
            ):
                try:
                    value = mol.GetProp(prop_name)
                    props[prop_name] = value
                except Exception:
                    props[prop_name] = ""

        yield i, mol, props


# ---------------------------------------------------------------------------
# CSV molecule generator (streaming)
# ---------------------------------------------------------------------------


def iter_csv_rows(
    filepath: str,
    smiles_col: str = "SMILES",
    max_scan: int = 0,
) -> Generator[Tuple[int, Dict[str, str]], None, None]:
    """
    Streaming generator over CSV rows.
    Yields (index, row_dict) for each row.

    Args:
        filepath: Path to CSV file
        smiles_col: Column name containing SMILES strings
        max_scan: If > 0, stop after N rows

    Yields:
        (row_index, row_dict)
    """
    with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if max_scan > 0 and i >= max_scan:
                break
            yield i, row


# ---------------------------------------------------------------------------
# Newline escaping for SDF ↔ CSV
# ---------------------------------------------------------------------------


def escape_newlines(value: str) -> str:
    """Escape literal newlines in SDF property values for CSV storage."""
    if value is None:
        return ""
    # Replace \r\n or \n with escape sequence
    return value.replace("\r\n", NEWLINE_ESCAPE).replace("\n", NEWLINE_ESCAPE).replace("\r", NEWLINE_ESCAPE)


def unescape_newlines(value: str) -> str:
    """Unescape newlines when writing from CSV back to SDF."""
    if value is None:
        return ""
    return value.replace(NEWLINE_ESCAPE, "\n")


def validate_no_raw_newlines(value: str, field_name: str = "") -> None:
    """
    Validate that a CSV value contains no raw newlines (only escaped ones).
    Raises ValueError if raw newlines are found.

    Args:
        value: The string value to check
        field_name: Optional field name for error message context

    Raises:
        ValueError: If raw newlines (\\r or \\n, not preceded by backslash-escape) are found
    """
    if value is None:
        return
    # Check for raw newlines that aren't part of our escape sequence
    # We allow our \\n escapes but not raw \\r, \\r\\n, or standalone \\n
    # Strip known escaped sequences and check what remains
    cleaned = value.replace(NEWLINE_ESCAPE, "")
    if "\r" in cleaned or "\n" in cleaned:
        raise ValueError(
            f"Raw newline character found in CSV field '{field_name}'. "
            f"Multi-line values must use '{NEWLINE_ESCAPE}' escape. "
            f"Value: {value[:100]}..."
        )


# ---------------------------------------------------------------------------
# Chunked multiprocessing helpers
# ---------------------------------------------------------------------------


def parallel_map(
    func: Callable[[Any], Any],
    items: List[Any],
    workers: int = 0,
    chunk_size: int = 100,
    desc: str = "Processing",
    total: Optional[int] = None,
) -> List[Any]:
    """
    Apply func to items in parallel using multiprocessing.Pool,
    with tqdm progress bar.

    Args:
        func: Function to apply to each item
        items: List of items to process
        workers: Number of worker processes (0 = CPU count)
        chunk_size: Items per chunk for load balancing
        desc: Description for progress bar
        total: Total expected results (for tqdm)

    Returns:
        List of results in order of completion (not original order)
    """
    if workers <= 0:
        workers = max(1, cpu_count() - 1)

    if total is None:
        total = len(items)

    results = []
    with Pool(processes=workers) as pool:
        with tqdm(total=total, desc=desc, unit="mol") as pbar:
            for result in pool.imap_unordered(func, items, chunksize=chunk_size):
                results.append(result)
                pbar.update(1)

    return results


def chunk_items(items: List[Any], chunk_size: int) -> Generator[List[Any], None, None]:
    """Split a list into chunks of approximately chunk_size."""
    for i in range(0, len(items), chunk_size):
        yield items[i : i + chunk_size]


# ---------------------------------------------------------------------------
# Utility: build consistent fieldnames for SDF → CSV
# ---------------------------------------------------------------------------


# Metadata/ordering columns that should appear first (in this order) when present.
METADATA_COLUMNS = ["XmlIndex", "Title", "CompoundID", "Annotations"]


def build_ordered_fieldnames(
    discovered_properties: Set[str],
    extra_fields: Optional[List[str]] = None,
    include_standard_properties: bool = True,
) -> List[str]:
    """
    Build an ordered list of CSV column names.

    Order:
      1. Metadata columns (XmlIndex, Title, CompoundID, Annotations)
         when present.
      2. RDKit standard computed columns (SMILES, MolecularWeight, ...).
      3. Other discovered properties (sorted), e.g. SDF data tags.
      4. ChemDraw-sourced properties (``ChemDraw_*``), sorted, grouped last.
      5. Any extra fields.

    Args:
        discovered_properties: Set of property names found in the input
        extra_fields: Additional fixed column names to include
        include_standard_properties: Whether to include computed property columns

    Returns:
        Ordered list of field names (no duplicates)
    """
    discovered = set(discovered_properties)
    fieldnames: List[str] = []

    # 1. Metadata columns first (only those actually present).
    for name in METADATA_COLUMNS:
        if name in discovered:
            fieldnames.append(name)

    # 2. RDKit standard computed columns.
    if include_standard_properties:
        standard = [
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
        ]
        fieldnames.extend(standard)

    # 3 & 4. Remaining discovered properties: other props first, ChemDraw_* last.
    remaining = discovered - set(fieldnames)
    chemdraw_props = sorted(p for p in remaining if p.startswith("ChemDraw_"))
    other_props = sorted(p for p in remaining if not p.startswith("ChemDraw_"))
    fieldnames.extend(other_props)
    fieldnames.extend(chemdraw_props)

    # 5. Extra fields.
    if extra_fields:
        for field in extra_fields:
            if field not in fieldnames:
                fieldnames.append(field)

    return fieldnames