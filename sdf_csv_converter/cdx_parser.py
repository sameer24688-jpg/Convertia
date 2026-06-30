"""
CDX/CDXML parser for extracting molecular structures, titles, atom labels,
annotations, and ChemDraw properties.

Supports:
- CDXML (.cdxml): XML-based format, parsed with tree-based parsing
- CDX (.cdx): Binary format, converted to CDXML via OpenBabel first
- Auto-detection: files with .cdx extension that are actually CDXML are parsed directly

Key features:
- Namespace-agnostic XML parsing (handles both namespaced and bare CDXML)
- Page-level structures: each <fragment> that is a direct child of <page>, or a
  direct child of a page-level <group> (ChemDraw often wraps structures in
  groups), is processed as a separate structure
- Nickname / abbreviation expansion: atoms drawn as Me, OMe, Ph, Boc, ... carry
  ChemDraw's full expansion as an embedded <fragment> with an
  ExternalConnectionPoint marking the attachment. These are flattened into the
  parent structure (see ``_flatten_fragment``) so the real chemistry (oxygen of
  OMe, the phenyl ring, etc.) reaches the output instead of collapsing to a
  single carbon. Single-attachment only; multi-attachment linkers fall back to a
  single atom.
- R-groups: labels like R / R1 / R2 (and GenericNickname nodes) become RDKit
  dummy atoms (atomic number 0) with atom-map numbers, e.g. [*:1].
- Coordinate-based text assignment: page-level free text that is not a ChemDraw
  compound-name field (see ``chemicalproperty``) is assigned to the NEAREST
  fragment by position, not duplicated onto every fragment
- Compound names: ChemDraw ``chemicalproperty`` elements (type 1) link each
  structure to its caption ``<t>`` via ``BasisObjects`` and
  ``ChemicalPropertyDisplayID``; this is preferred over coordinate heuristics
- Explicit ordering: each structure carries xml_index/page_index so output row
  order is recoverable downstream
- Extracts per-fragment: title, atom labels, assigned annotations, compound id,
  and ChemProp* values (emitted under a ChemDraw_ prefix to avoid colliding
  with RDKit-computed properties)
- Builds RDKit Mol from CDXML atom/bond elements with stereo mapping

CDX binary support (via OpenBabel):
- Empty molecule filtering — Skips 0-atom molecules produced from drawing elements
- Consecutive-empty guard — Detects broken CDX files (e.g., ChemDraw 25.5) that cause
  OpenBabel to loop infinitely; terminates after 50 consecutive empty reads
- Duplicate detection — Prevents re-reading the same molecule via atom/bond hash

Limitations:
- 2D coordinates, bond display styles, arrows, and drawing elements are NOT preserved
- Complex stereochemistry may not survive roundtrip cleanly
- Multi-attachment nicknames (linkers/superatoms with 2+ ExternalConnectionPoints)
  are not expanded; they collapse to a single atom (graceful fallback)
- Bare abbreviation labels with no embedded fragment fall back to
  ``_label_to_atomic_num`` (single carbon for unknown groups)
- CDX binary support requires OpenBabel
"""
import logging
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, Generator, List, Optional, Set, Tuple

from rdkit import Chem

logger = logging.getLogger(__name__)

# ChemProp property name mappings (CDXML attribute -> human-readable name)
CHEMPROP_MAP = {
    "ChemPropName": "Name",
    "ChemPropFormula": "ChemicalFormula",
    "ChemPropExactMass": "ExactMass",
    "ChemPropMolWt": "MolecularWeight",
    "ChemPropMOverZ": "MOverZ",
    "ChemPropAnalysis": "ElementalAnalysis",
    "ChemPropBoilingPoint": "BoilingPoint",
    "ChemPropMeltingPoint": "MeltingPoint",
    "ChemPropCriticalTemp": "CriticalTemperature",
    "ChemPropCriticalPres": "CriticalPressure",
    "ChemPropCriticalVol": "CriticalVolume",
    "ChemPropGibbs": "GibbsFreeEnergy",
    "ChemPropLogP": "LogP",
    "ChemPropCLogP": "CLogP",
    "ChemPropMR": "MolarRefractivity",
    "ChemPropHenry": "HenrysLawConstant",
    "ChemPropEFormation": "HeatOfFormation",
    "ChemPropTPSA": "TPSA",
    "ChemPropHBA": "HBA",
    "ChemPropHBD": "HBD",
}

# CDXML Display attribute -> RDKit BondDir mapping
DISPLAY_TO_BONDDIR = {
    "WedgedHash": Chem.BondDir.BEGINWEDGE,
    "WedgedHashDown": Chem.BondDir.BEGINDASH,
    "Bold": Chem.BondDir.BEGINWEDGE,
    "Dashed": Chem.BondDir.BEGINDASH,
}


# Heuristic for compound-style identifiers (e.g. "PROJ-42", "LAB-059").
# Matches a single token of letters/digits joined by '-' or '_', or a
# letter-prefixed numeric code. Used only to surface a CompoundID column.
_COMPOUND_ID_RE = re.compile(
    r"^[A-Za-z][A-Za-z0-9]*(?:[-_][A-Za-z0-9]+)+$|^[A-Za-z]{2,}\d+$"
)

# R-group labels: "R" (generic), "R1".."Rn" (numbered). Used to map ChemDraw
# R-groups onto RDKit dummy atoms (atomic number 0) with atom-map numbers.
_RGROUP_RE = re.compile(r"^R(\d+)$")
# Other generic-substituent placeholders that ChemDraw users draw as variable
# attachment points. Mapped to an unnumbered dummy atom (map number 0).
_GENERIC_RGROUP_LABELS = {"R", "X", "Y", "Z"}


@dataclass
class CDXStructure:
    """Represents a single molecular structure extracted from CDX/CDXML."""

    mol: Optional[Chem.Mol] = None
    smiles: str = ""
    title: str = ""
    atom_labels: Dict[int, str] = field(default_factory=dict)
    annotations: List[str] = field(default_factory=list)
    chem_props: Dict[str, str] = field(default_factory=dict)
    fragment_id: str = ""
    # Ordering metadata (set during parsing so output sequence is explicit
    # and stable even if a downstream tool reorders rows).
    xml_index: int = 0
    page_index: int = 0
    # Compound identifier assigned from a nearby page-level text, if detected.
    compound_id: str = ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_cdx_or_cdxml(
    filepath: str,
    max_structures: int = 0,
) -> Generator[CDXStructure, None, None]:
    """Auto-detect CDX vs CDXML and parse accordingly."""
    ext = filepath.lower().rsplit(".", 1)[-1] if "." in filepath else ""
    is_xml = _is_xml_file(filepath)

    if ext == "cdxml" or (ext == "cdx" and is_xml):
        yield from parse_cdxml_streaming(filepath, max_structures)
    elif ext == "cdx":
        logger.info(f"Converting CDX binary to CDXML via OpenBabel: {filepath}")
        cdxml_str = parse_cdx_via_openbabel(filepath)
        yield from parse_cdxml_from_string(cdxml_str, max_structures)
    else:
        if is_xml:
            yield from parse_cdxml_streaming(filepath, max_structures)
        else:
            logger.info(f"Trying CDX binary conversion: {filepath}")
            cdxml_str = parse_cdx_via_openbabel(filepath)
            yield from parse_cdxml_from_string(cdxml_str, max_structures)


def parse_cdxml_streaming(
    filepath: str,
    max_structures: int = 0,
) -> Generator[CDXStructure, None, None]:
    """
    Parse a CDXML file. Processes page-level structure fragments (direct
    children of <page>, or of page-level <group> elements); nested fragments
    inside nickname atoms (e.g. "Me", "OMe") are not treated as separate
    structures. Page-level free text is assigned to the nearest fragment by
    coordinates (see ``_iter_page_structures``).
    """
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except ET.ParseError as e:
        logger.error(f"XML parse error in {filepath}: {e}")
        return
    except Exception as e:
        logger.error(f"Error parsing CDXML {filepath}: {e}")
        return

    yield from _iter_page_structures(root, max_structures)


def parse_cdxml_from_string(
    cdxml_string: str,
    max_structures: int = 0,
) -> Generator[CDXStructure, None, None]:
    """Parse a CDXML string (e.g., from OpenBabel conversion of CDX)."""
    try:
        root = ET.fromstring(cdxml_string)
    except ET.ParseError as e:
        logger.error(f"Failed to parse CDXML string: {e}")
        return

    yield from _iter_page_structures(root, max_structures)


def _iter_page_structures(
    root: ET.Element,
    max_structures: int = 0,
) -> Generator[CDXStructure, None, None]:
    """
    Shared CDXML walk used by both the file and string parsers.

    For each <page>:
    1. Collect every page-level structure fragment and its center coordinate.
    2. Assign compound names from ChemDraw ``chemicalproperty`` links (type 1).
    3. Assign remaining page-level ``<t>`` text to the nearest fragment by
       coordinates (compound IDs, captions, etc.).
    4. Yield structures in document order, stamping ``xml_index``/``page_index``
       and detecting a ``compound_id`` from assigned text.
    """
    doc_chem_props: Dict[str, str] = {}
    for attr_name, prop_name in CHEMPROP_MAP.items():
        val = root.attrib.get(attr_name, "")
        if val:
            doc_chem_props[prop_name] = val

    structure_count = 0

    for page_index, page in enumerate(_find_children(root, "page")):
        id_map = _page_id_map(page)

        # Build every page-level structure fragment first.
        structures: List[CDXStructure] = []
        centers: List[Optional[Tuple[float, float]]] = []
        fragment_ids: List[str] = []
        group_ids: List[str] = []
        for frag_elem, group_id in _iter_page_level_fragment_entries(page):
            fragment_atoms: Dict[int, ET.Element] = {}
            fragment_bonds: List[ET.Element] = []
            fragment_texts: List[ET.Element] = []
            fragment_id = frag_elem.attrib.get("id", "")

            for child in frag_elem:
                child_tag = _local_tag(child.tag)
                if child_tag == "n":
                    atom_id = child.attrib.get("id", "")
                    if atom_id:
                        try:
                            fragment_atoms[int(atom_id)] = child
                        except ValueError:
                            pass
                elif child_tag == "b":
                    fragment_bonds.append(child)
                elif child_tag == "t":
                    fragment_texts.append(child)

            structure = _build_structure(
                frag_elem,
                fragment_atoms,
                fragment_bonds,
                fragment_texts,
                fragment_id,
                doc_chem_props,
            )
            structures.append(structure)
            centers.append(_fragment_center(frag_elem, fragment_atoms))
            fragment_ids.append(fragment_id)
            group_ids.append(group_id)

        # ChemDraw compound names: chemicalproperty -> caption <t> via BasisObjects.
        title_display_ids = _assign_titles_from_chemical_properties(
            page, structures, fragment_ids, group_ids, id_map
        )

        # Remaining page-level text (not already used as a compound name).
        if structures:
            for t_elem in _find_children(page, "t"):
                t_id = t_elem.attrib.get("id", "")
                if t_id and t_id in title_display_ids:
                    continue
                text = _text_string(t_elem)
                if not text:
                    continue
                structures[_nearest_index(centers, _text_point(t_elem))].annotations.append(text)

        # Yield in document order with explicit ordering + compound id.
        for structure in structures:
            structure.page_index = page_index
            structure.xml_index = structure_count
            structure.compound_id = _detect_compound_id(structure.annotations)
            yield structure
            structure_count += 1
            if max_structures > 0 and structure_count >= max_structures:
                return


def parse_cdx_via_openbabel(filepath: str) -> str:
    """Convert a binary CDX file to CDXML string using OpenBabel."""
    import tempfile

    try:
        from openbabel import openbabel as ob
    except ImportError:
        raise RuntimeError(
            "This is a binary CDX file. OpenBabel is required for CDX conversion.\n"
            "Install with: pip install openbabel\n"
            "Or export your file as CDXML from ChemDraw (File -> Save As -> CDXML)."
        )

    tmp_path = None
    try:
        conv = ob.OBConversion()
        conv.SetInAndOutFormats("cdx", "cdxml")

        fd, tmp_path = tempfile.mkstemp(suffix=".cdxml", prefix="ob_conv_")
        os.close(fd)

        mol = ob.OBMol()
        notatend = conv.ReadFile(mol, filepath)
        if not notatend:
            raise RuntimeError(
                f"OpenBabel could not read CDX file: {filepath}\n"
                "The file may be corrupted or in an unsupported CDX version."
            )

        # Filter out empty molecules (0 atoms) that OpenBabel may produce
        # from CDX drawing elements that aren't chemical structures
        mols = []
        seen_hashes = set()
        MAX_MOLS = 500
        mol_count = 0  # Reset: count only valid molecules
        MAX_CONSECUTIVE_EMPTY = 50  # Guard against infinite loops on broken CDX

        # Check first molecule
        if mol.NumAtoms() > 0:
            mol_hash = mol.NumAtoms() * 10000 + mol.NumBonds()
            if mol_hash not in seen_hashes:
                seen_hashes.add(mol_hash)
                mols.append(ob.OBMol(mol))
                mol_count += 1

        # Read subsequent molecules, filtering empties and duplicates
        # Some broken CDX files (e.g., ChemDraw 25.5) cause OpenBabel to
        # loop infinitely returning empty mols — cap consecutive empty reads
        consecutive_empty = 0
        while conv.Read(mol) and mol_count < MAX_MOLS:
            if mol.NumAtoms() == 0:
                consecutive_empty += 1
                if consecutive_empty > MAX_CONSECUTIVE_EMPTY:
                    logger.warning(
                        f"CDX file produced {consecutive_empty} consecutive "
                        f"empty molecules — stopping (file may be corrupted)"
                    )
                    break
                continue
            consecutive_empty = 0
            mol_hash = mol.NumAtoms() * 10000 + mol.NumBonds()
            if mol_hash in seen_hashes:
                continue
            seen_hashes.add(mol_hash)
            mols.append(ob.OBMol(mol))
            mol_count += 1

        logger.info(f"Read {mol_count} molecules from CDX file")

        with open(tmp_path, "w") as outf:
            out_conv = ob.OBConversion()
            out_conv.SetInAndOutFormats("cdx", "cdxml")
            for m in mols:
                cdxml_str = out_conv.WriteString(m)
                if cdxml_str:
                    outf.write(cdxml_str)
                    outf.write("\n")

        file_size = os.path.getsize(tmp_path)
        if file_size == 0:
            raise RuntimeError(
                f"OpenBabel produced empty CDXML from: {filepath}\n"
                "The CDX file may contain only drawing elements with no chemical structures."
            )

        with open(tmp_path, "r", encoding="utf-8", errors="replace") as f:
            result = f.read()

        return result

    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"OpenBabel CDX conversion error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _is_chemprop_label_template(value: str) -> bool:
    """
    True if a ChemProp value is just a label template with no data, e.g.
    ChemDraw's document defaults like "Molecular Weight: " or "Log P: ".
    Such templates end with a colon once stripped of trailing whitespace.
    """
    return value.rstrip().endswith(":")


def structure_to_properties_dict(structure: CDXStructure) -> Dict[str, str]:
    """
    Convert a CDXStructure to a flat properties dict for CSV/SDF output.

    Naming conventions (to avoid silently overwriting RDKit-computed values):
    - Ordering/metadata columns use bare names: XmlIndex, Title, CompoundID,
      Annotations.
    - ChemDraw-sourced properties are prefixed ``ChemDraw_`` (e.g.
      ChemDraw_MolecularWeight) so they never collide with RDKit columns.
    - Empty ChemProp label templates (e.g. "Molecular Weight: ") are dropped.
    """
    props: Dict[str, str] = {}

    # Explicit ordering index so output sequence is recoverable downstream.
    props["XmlIndex"] = str(structure.xml_index)

    if structure.title:
        props["Title"] = structure.title

    if structure.compound_id:
        props["CompoundID"] = structure.compound_id

    if structure.annotations:
        props["Annotations"] = " | ".join(structure.annotations)

    for prop_name, prop_value in structure.chem_props.items():
        if not prop_value or not prop_value.strip():
            continue
        if _is_chemprop_label_template(prop_value):
            continue
        props[f"ChemDraw_{prop_name}"] = prop_value

    return props


# ---------------------------------------------------------------------------
# Internal helpers — namespace-agnostic XML utilities
# ---------------------------------------------------------------------------


def _is_xml_file(filepath: str) -> bool:
    """Check if a file starts with XML declaration or CDXML root tag."""
    try:
        with open(filepath, "rb") as f:
            header = f.read(200)
        return header.startswith(b"<?xml") or header.startswith(b"<CDXML") or header.startswith(b"<!")
    except Exception:
        return False


def _local_tag(tag: str) -> str:
    """Strip namespace from a tag."""
    return tag.split("}")[-1] if "}" in tag else tag


def _find_child(elem: ET.Element, tag: str) -> Optional[ET.Element]:
    """Find a child element by local tag name, namespace-agnostic."""
    for child in elem:
        if _local_tag(child.tag) == tag:
            return child
    return None


def _find_children(elem: ET.Element, tag: str) -> List[ET.Element]:
    """Find all direct child elements by local tag name, namespace-agnostic."""
    return [child for child in elem if _local_tag(child.tag) == tag]


def _iter_page_level_fragments(
    page: ET.Element,
) -> Generator[ET.Element, None, None]:
    """
    Yield structure-bearing ``<fragment>`` elements at page scope, in document order.

    ChemDraw often wraps each structure in a ``<group>`` that is a direct child
    of ``<page>``. Fragments nested inside nickname atoms (abbreviation
    expansions) are intentionally excluded — only page-level fragments and
    fragments inside page-level groups (recursively) are yielded.
    """
    for frag_elem, _group_id in _iter_page_level_fragment_entries(page):
        yield frag_elem


def _iter_page_level_fragment_entries(
    page: ET.Element,
) -> Generator[Tuple[ET.Element, str], None, None]:
    """Yield ``(fragment, parent_group_id)`` pairs in document order."""
    for child in page:
        tag = _local_tag(child.tag)
        if tag == "fragment":
            yield child, ""
        elif tag == "group":
            group_id = child.attrib.get("id", "")
            for frag_elem in _iter_group_fragments(child):
                yield frag_elem, group_id


def _iter_group_fragments(
    group: ET.Element,
) -> Generator[ET.Element, None, None]:
    """Yield structure fragments inside a ``<group>``, in document order."""
    for child in group:
        tag = _local_tag(child.tag)
        if tag == "fragment":
            yield child
        elif tag == "group":
            yield from _iter_group_fragments(child)


def _page_id_map(page: ET.Element) -> Dict[str, ET.Element]:
    """Map ChemDraw object id attributes to elements under a page."""
    id_map: Dict[str, ET.Element] = {}
    for elem in page.iter():
        elem_id = elem.attrib.get("id")
        if elem_id:
            id_map[elem_id] = elem
    return id_map


def _assign_titles_from_chemical_properties(
    page: ET.Element,
    structures: List[CDXStructure],
    fragment_ids: List[str],
    group_ids: List[str],
    id_map: Dict[str, ET.Element],
) -> Set[str]:
    """
    Assign ``structure.title`` from ChemDraw ``chemicalproperty`` name fields.

    ChemDraw stores compound names as page-level caption ``<t>`` elements
    referenced by ``ChemicalPropertyDisplayID``, with ``BasisObjects`` listing
    the fragment/group/atom ids that belong to that structure.

    Returns the set of caption ``<t>`` element ids consumed as titles so they
    are not duplicated into ``annotations`` by the coordinate heuristic.
    """
    used_display_ids: Set[str] = set()
    if not structures:
        return used_display_ids

    for cp in _find_children(page, "chemicalproperty"):
        # Type 1 is the compound-name field in ChemDraw exports.
        if cp.attrib.get("ChemicalPropertyType", "1") != "1":
            continue
        disp_id = cp.attrib.get("ChemicalPropertyDisplayID", "")
        if not disp_id:
            continue
        disp_elem = id_map.get(disp_id)
        if disp_elem is None:
            continue
        title = _text_string(disp_elem)
        if not title:
            continue
        basis = set(cp.attrib.get("BasisObjects", "").split())

        for i, (frag_id, group_id) in enumerate(zip(fragment_ids, group_ids)):
            if (frag_id and frag_id in basis) or (group_id and group_id in basis):
                structures[i].title = title
                used_display_ids.add(disp_id)
                break

    return used_display_ids


def _int_attr(elem: ET.Element, name: str) -> Optional[int]:
    """Read an integer attribute, returning None when absent or non-numeric."""
    try:
        return int(elem.attrib[name])
    except (KeyError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Internal helpers — nickname / abbreviation / R-group detection
# ---------------------------------------------------------------------------


def _nickname_fragment(n_elem: ET.Element) -> Optional[ET.Element]:
    """
    Return the embedded child ``<fragment>`` of an atom node, or None.

    ChemDraw serializes an abbreviation/nickname (Me, OMe, Ph, Boc, ...) as an
    ``<n>`` that contains the full expansion as a nested ``<fragment>`` plus an
    ``ExternalConnectionPoint`` marking where it attaches. The presence of that
    child fragment is the signal that the node can be expanded in place.
    """
    return _find_child(n_elem, "fragment")


def _is_external_connection_point(n_elem: ET.Element) -> bool:
    """True if an atom node is an ExternalConnectionPoint (the attachment marker
    inside a nickname's embedded fragment, not a real atom)."""
    return n_elem.attrib.get("NodeType", "") == "ExternalConnectionPoint"


def _rgroup_map_number(label: str) -> Optional[int]:
    """
    Map an R-group / generic-substituent label to an RDKit atom-map number.

    - ``"R1"`` -> 1, ``"R2"`` -> 2, ... (numbered R-groups keep their number)
    - ``"R"``, ``"X"``, ``"Y"``, ``"Z"`` -> 0 (generic, unnumbered dummy)
    - anything else (real element labels like ``"OH"``, ``"N"``) -> None

    Returns None for non-R-group labels so normal heteroatom handling is
    unaffected.
    """
    label = (label or "").strip()
    if not label:
        return None
    if label in _GENERIC_RGROUP_LABELS:
        return 0
    m = _RGROUP_RE.match(label)
    if m:
        return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Internal helpers — geometry and coordinate-based text assignment
# ---------------------------------------------------------------------------


def _parse_point(value: str) -> Optional[Tuple[float, float]]:
    """Parse a CDXML 'p' coordinate attribute ('x y') into (x, y) floats."""
    if not value:
        return None
    parts = value.split()
    if len(parts) < 2:
        return None
    try:
        return (float(parts[0]), float(parts[1]))
    except ValueError:
        return None


def _bbox_center(value: str) -> Optional[Tuple[float, float]]:
    """Parse a CDXML 'BoundingBox' ('x1 y1 x2 y2') into its center point."""
    if not value:
        return None
    parts = value.split()
    if len(parts) < 4:
        return None
    try:
        x1, y1, x2, y2 = (float(parts[0]), float(parts[1]),
                          float(parts[2]), float(parts[3]))
    except ValueError:
        return None
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _nearest_index(
    centers: List[Optional[Tuple[float, float]]],
    point: Optional[Tuple[float, float]],
) -> int:
    """
    Return the index of the nearest center to ``point`` by squared Euclidean
    distance. Centers that are None are skipped. Falls back to index 0 when the
    point or all centers are unknown, so text is never silently dropped.
    """
    if point is None or not centers:
        return 0
    best_i = 0
    best_d: Optional[float] = None
    for i, c in enumerate(centers):
        if c is None:
            continue
        d = (c[0] - point[0]) ** 2 + (c[1] - point[1]) ** 2
        if best_d is None or d < best_d:
            best_d = d
            best_i = i
    return best_i


def _text_string(t_elem: ET.Element) -> str:
    """Concatenate all <s> run texts inside a <t> element, stripped."""
    parts: List[str] = []
    for s_elem in _find_children(t_elem, "s"):
        if s_elem.text:
            parts.append(s_elem.text)
    return "".join(parts).strip()


def _text_point(t_elem: ET.Element) -> Optional[Tuple[float, float]]:
    """Best-effort position of a <t> element: 'p' first, then BoundingBox center."""
    point = _parse_point(t_elem.attrib.get("p", ""))
    if point is not None:
        return point
    return _bbox_center(t_elem.attrib.get("BoundingBox", ""))


def _fragment_center(
    frag_elem: ET.Element,
    atoms: Dict[int, ET.Element],
) -> Optional[Tuple[float, float]]:
    """Center of a fragment: BoundingBox center, else mean of atom points."""
    center = _bbox_center(frag_elem.attrib.get("BoundingBox", ""))
    if center is not None:
        return center
    points = [
        p for p in (_parse_point(n.attrib.get("p", "")) for n in atoms.values())
        if p is not None
    ]
    if not points:
        return None
    n = len(points)
    return (sum(x for x, _ in points) / n, sum(y for _, y in points) / n)


def _detect_compound_id(annotations: List[str]) -> str:
    """
    Return the first annotation line that looks like a compound identifier
    (e.g. 'PROJ-42', 'LAB-059'), or '' if none match. Splits multi-line
    annotations so codes stored with a secondary line still match.
    """
    for annotation in annotations:
        for line in annotation.splitlines():
            token = line.strip()
            if token and _COMPOUND_ID_RE.match(token):
                return token
    return ""


def _build_structure(
    frag_elem: ET.Element,
    fragment_atoms: Dict[int, ET.Element],
    fragment_bonds: List[ET.Element],
    fragment_texts: List[ET.Element],
    fragment_id: str,
    doc_chem_props: Dict[str, str],
) -> CDXStructure:
    """Build a CDXStructure from parsed fragment data.

    Note: page-level free text is assigned by the caller
    (``_iter_page_structures``) using coordinates, not here.
    """
    structure = CDXStructure(fragment_id=fragment_id)

    # Extract title from text elements (first text = title)
    fragment_title = ""
    for t_elem in fragment_texts:
        s_elem = _find_child(t_elem, "s")
        if s_elem is not None and s_elem.text:
            text = s_elem.text.strip()
            if text and not fragment_title:
                fragment_title = text
            elif text:
                structure.annotations.append(text)

    structure.title = fragment_title

    # Extract atom labels (text inside <n> elements)
    for atom_id, n_elem in fragment_atoms.items():
        for child in n_elem:
            child_tag = _local_tag(child.tag)
            if child_tag == "t":
                s_elem = _find_child(child, "s")
                if s_elem is not None and s_elem.text:
                    label = s_elem.text.strip()
                    if label:
                        structure.atom_labels[atom_id] = label

    # Extract ChemProp values from fragment
    for attr_name, prop_name in CHEMPROP_MAP.items():
        val = frag_elem.attrib.get(attr_name, "")
        if val:
            structure.chem_props[prop_name] = val

    # Merge document-level ChemProps (fragment-level overrides)
    merged_props = dict(doc_chem_props)
    merged_props.update(structure.chem_props)
    structure.chem_props = merged_props

    # Flatten embedded nickname fragments (OMe, Ph, Boc, ...) into atoms/bonds,
    # then build. Any failure in expansion falls back to the raw atoms/bonds so
    # a single odd nickname can never abort the whole conversion.
    try:
        flat_atoms, bond_specs = _flatten_fragment(fragment_atoms, fragment_bonds)
    except Exception as e:
        logger.debug(
            f"Nickname expansion failed for fragment {fragment_id}: {e}; "
            "falling back to unexpanded atoms"
        )
        flat_atoms = fragment_atoms
        bond_specs = [s for s in (_bond_spec(b) for b in fragment_bonds) if s]

    # Build RDKit Mol from the flattened atoms and bond specs
    mol = _build_rdkit_mol(flat_atoms, bond_specs)
    if mol is not None:
        try:
            Chem.SanitizeMol(mol)
            structure.mol = mol
            structure.smiles = Chem.MolToSmiles(mol, canonical=True)
        except Exception as e:
            logger.warning(f"Failed to sanitize mol in fragment {fragment_id}: {e}")
            try:
                structure.smiles = Chem.MolToSmiles(mol, canonical=True)
                structure.mol = mol
            except Exception:
                pass

    return structure


# ---------------------------------------------------------------------------
# Internal helpers — nickname expansion (flattening embedded fragments)
# ---------------------------------------------------------------------------

# A lightweight bond description decoupled from the source <b> element so that
# expanded (inner-fragment) bonds and remapped outer bonds share one code path.
BondSpec = Tuple[int, int, str, str]  # (begin_id, end_id, order, display)


def _bond_spec(b_elem: ET.Element) -> Optional[BondSpec]:
    """Normalize a CDXML ``<b>`` element into a (begin, end, order, display)
    tuple, or None when endpoints are missing/non-numeric."""
    begin = _int_attr(b_elem, "B")
    end = _int_attr(b_elem, "E")
    if begin is None or end is None:
        return None
    return (
        begin,
        end,
        b_elem.attrib.get("Order", "1"),
        b_elem.attrib.get("Display", ""),
    )


def _flatten_fragment(
    atoms: Dict[int, ET.Element],
    bonds: List[ET.Element],
) -> Tuple[Dict[int, ET.Element], List[BondSpec]]:
    """
    Expand embedded nickname fragments into the parent fragment.

    For each atom node that carries an embedded ``<fragment>`` (a nickname such
    as OMe/Ph/Boc), replace it with the atoms of that fragment and rewire the
    bond that pointed at the nickname onto the fragment's attachment atom (the
    neighbour of its single ``ExternalConnectionPoint``). The ECP and its bond
    are dropped. Nested nicknames are expanded recursively.

    Single-attachment only: a fragment with zero or 2+ ExternalConnectionPoints
    (a linker/superatom) is left collapsed to a single atom so downstream
    handling degrades gracefully. Returns (flat_atoms, bond_specs).
    """
    flat_atoms: Dict[int, ET.Element] = {}
    remap: Dict[int, int] = {}
    expanded_specs: List[BondSpec] = []

    for atom_id, n_elem in atoms.items():
        inner = _nickname_fragment(n_elem)
        if inner is None:
            flat_atoms[atom_id] = n_elem
            continue
        expansion = _expand_nickname(inner)
        if expansion is None:
            # 0 or 2+ attachment points, or malformed -> keep as single atom.
            flat_atoms[atom_id] = n_elem
            continue
        sub_atoms, sub_specs, attachment_id = expansion
        flat_atoms.update(sub_atoms)
        expanded_specs.extend(sub_specs)
        remap[atom_id] = attachment_id

    bond_specs: List[BondSpec] = []
    for b_elem in bonds:
        spec = _bond_spec(b_elem)
        if spec is None:
            continue
        begin, end, order, display = spec
        bond_specs.append(
            (remap.get(begin, begin), remap.get(end, end), order, display)
        )
    bond_specs.extend(expanded_specs)
    return flat_atoms, bond_specs


def _expand_nickname(
    inner: ET.Element,
) -> Optional[Tuple[Dict[int, ET.Element], List[BondSpec], int]]:
    """
    Flatten a single nickname's embedded ``<fragment>``.

    Returns (sub_atoms, sub_bond_specs, attachment_id) where the ECP atom and
    its bond have been removed, or None if the fragment is not a clean
    single-attachment group (so the caller can fall back).
    """
    inner_atoms: Dict[int, ET.Element] = {}
    inner_bond_elems: List[ET.Element] = []
    for child in inner:
        tag = _local_tag(child.tag)
        if tag == "n":
            iid = _int_attr(child, "id")
            if iid is None:
                return None
            inner_atoms[iid] = child
        elif tag == "b":
            inner_bond_elems.append(child)

    # Recursively expand nicknames nested inside this fragment. ECP nodes carry
    # no embedded fragment, so they pass through untouched and are resolved here.
    flat_atoms, flat_specs = _flatten_fragment(inner_atoms, inner_bond_elems)

    ecp_ids = [
        i for i, a in flat_atoms.items() if _is_external_connection_point(a)
    ]
    if len(ecp_ids) != 1:
        return None  # zero or multi-attachment -> not supported, fall back
    ecp_id = ecp_ids[0]

    attachment_id: Optional[int] = None
    kept_specs: List[BondSpec] = []
    for begin, end, order, display in flat_specs:
        if begin == ecp_id:
            if attachment_id is None:
                attachment_id = end
        elif end == ecp_id:
            if attachment_id is None:
                attachment_id = begin
        else:
            kept_specs.append((begin, end, order, display))

    if attachment_id is None:
        return None  # ECP not bonded -> malformed, fall back

    flat_atoms.pop(ecp_id, None)
    return flat_atoms, kept_specs, attachment_id


def _build_rdkit_mol(
    atoms: Dict[int, ET.Element],
    bond_specs: List[BondSpec],
) -> Optional[Chem.Mol]:
    """
    Build an RDKit RWMol from flattened CDXML atoms and bond specs.

    Atoms are the post-expansion ``<n>`` elements (nicknames already flattened
    by :func:`_flatten_fragment`); bonds are normalized
    (begin, end, order, display) tuples. Handles:
    - Element attribute (atomic number)
    - R-group / generic labels (R, R1, X, ...) -> dummy atoms with map numbers
    - Atom labels (OH, NH, CH3, etc.) for heteroatoms with explicit H
    - NumHydrogens attribute
    - Bond stereo (Display -> BondDir)
    """
    if not atoms:
        return None

    try:
        mol = Chem.RWMol()
        id_to_idx: Dict[int, int] = {}

        # Add atoms
        for atom_id, n_elem in sorted(atoms.items()):
            element = n_elem.attrib.get("Element", "")
            num_hydrogens = n_elem.attrib.get("NumHydrogens", "")
            node_type = n_elem.attrib.get("NodeType", "")

            # Get atom label (text inside <n>)
            label = ""
            for child in n_elem:
                if _local_tag(child.tag) == "t":
                    s_elem = _find_child(child, "s")
                    if s_elem is not None and s_elem.text:
                        label = s_elem.text.strip()
                        break

            # R-groups / generic attachment points -> RDKit dummy atoms (*)
            # carrying an atom-map number, instead of defaulting to carbon.
            rgroup_num = _rgroup_map_number(label)
            if rgroup_num is None and node_type == "GenericNickname":
                rgroup_num = 0
            if rgroup_num is not None:
                rdatom = Chem.Atom(0)
                rdatom.SetAtomMapNum(rgroup_num)
                idx = mol.AddAtom(rdatom)
                id_to_idx[atom_id] = idx
                continue

            # Determine atomic number
            atomic_num = 6  # Default carbon

            if element:
                try:
                    atomic_num = int(element)
                except ValueError:
                    atom = Chem.Atom(element)
                    atomic_num = atom.GetAtomicNum()
            elif label:
                atomic_num = _label_to_atomic_num(label)

            rdatom = Chem.Atom(atomic_num)

            # Isotope
            isotope = n_elem.attrib.get("Isotope", "")
            if isotope:
                try:
                    rdatom.SetIsotope(int(isotope))
                except ValueError:
                    pass

            # Charge
            charge = n_elem.attrib.get("Charge", "0")
            try:
                rdatom.SetFormalCharge(int(charge))
            except ValueError:
                pass

            # Radical
            radical = n_elem.attrib.get("Radical", "0")
            if radical == "1":
                rdatom.SetNumRadicalElectrons(1)
            elif radical == "2":
                rdatom.SetNumRadicalElectrons(2)

            # NumHydrogens — set explicit H count
            if num_hydrogens:
                try:
                    h_count = int(num_hydrogens)
                    rdatom.SetNumExplicitHs(h_count)
                except ValueError:
                    pass

            idx = mol.AddAtom(rdatom)
            id_to_idx[atom_id] = idx

        # Add bonds
        for a1, a2, order_str, display in bond_specs:
            if a1 not in id_to_idx or a2 not in id_to_idx:
                continue

            idx1 = id_to_idx[a1]
            idx2 = id_to_idx[a2]

            # Map bond order
            order_map = {
                "1": Chem.BondType.SINGLE,
                "2": Chem.BondType.DOUBLE,
                "3": Chem.BondType.TRIPLE,
                "1.5": Chem.BondType.AROMATIC,
                "aromatic": Chem.BondType.AROMATIC,
            }
            bond_type = order_map.get(order_str, Chem.BondType.SINGLE)

            bond_idx = mol.AddBond(idx1, idx2, bond_type)

            # Map stereo from Display attribute
            if display:
                bond_dir = DISPLAY_TO_BONDDIR.get(display)
                if bond_dir is not None:
                    try:
                        mol.GetBondWithIdx(bond_idx).SetBondDir(bond_dir)
                    except Exception:
                        pass

        result = mol.GetMol()
        return result

    except Exception as e:
        logger.warning(f"Failed to build RDKit mol from CDXML: {e}")
        return None


def _label_to_atomic_num(label: str) -> int:
    """
    Extract atomic number from an atom label like 'OH', 'NH', 'CH3', 'N', 'O', 'Br'.
    Returns 6 (carbon) as default.
    Handles nickname/abbreviation labels (Me, OMe, Ph, etc.) by returning carbon.
    """
    label = label.strip()
    if not label:
        return 6

    # Common element labels in CDXML (label -> atomic number)
    element_labels = {
        "O": 8, "OH": 8,
        "N": 7, "NH": 7, "NH2": 7, "NH3": 7,
        "S": 16, "SH": 16,
        "F": 9, "Cl": 17, "Br": 35, "I": 53,
        "P": 15,
        "B": 5,
        "Si": 14,
        "H": 1,
    }

    if label in element_labels:
        return element_labels[label]

    # Nickname/abbreviation labels — these are carbon-based groups
    # (Me, OMe, Et, Pr, Bu, Ph, Bn, Ac, etc.)
    # Don't try to parse as element — just return carbon
    nickname_labels = {
        "Me", "OMe", "Ome", "Et", "Pr", "iPr", "Bu", "tBu", "nBu",
        "Ph", "Bn", "Ac", "OAc", "Boc", "TMS", "TBS", "TFA",
        "CH3", "CH2", "CH",
        "CN", "CF3", "OCF3", "SCF3",
        "COOH", "CO2H", "CHO", "NO2", "SO2", "SO3H",
        "Ts", "Ms", "Tf", "Ns",
        "Cbz", "Fmoc", "Alloc", "Troc",
    }
    if label in nickname_labels:
        return 6

    # Try to match a valid element symbol (1-2 letters)
    # Use a safe lookup instead of Chem.Atom() which throws post-condition violations
    valid_elements = {
        "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9, "Ne": 10,
        "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17, "Ar": 18,
        "K": 19, "Ca": 20, "Sc": 21, "Ti": 22, "V": 23, "Cr": 24, "Mn": 25, "Fe": 26,
        "Co": 27, "Ni": 28, "Cu": 29, "Zn": 30, "Ga": 31, "Ge": 32, "As": 33, "Se": 34,
        "Br": 35, "Kr": 36, "Rb": 37, "Sr": 38, "Y": 39, "Zr": 40, "Nb": 41, "Mo": 42,
        "Tc": 43, "Ru": 44, "Rh": 45, "Pd": 46, "Ag": 47, "Cd": 48, "In": 49, "Sn": 50,
        "Sb": 51, "Te": 52, "I": 53, "Xe": 54, "Cs": 55, "Ba": 56, "La": 57, "Ce": 58,
        "Pr": 59, "Nd": 60, "Pm": 61, "Sm": 62, "Eu": 63, "Gd": 64, "Tb": 65, "Dy": 66,
        "Ho": 67, "Er": 68, "Tm": 69, "Yb": 70, "Lu": 71, "Hf": 72, "Ta": 73, "W": 74,
        "Re": 75, "Os": 76, "Ir": 77, "Pt": 78, "Au": 79, "Hg": 80, "Tl": 81, "Pb": 82,
        "Bi": 83, "Po": 84, "At": 85, "Rn": 86, "Fr": 87, "Ra": 88, "Ac": 89, "Th": 90,
        "Pa": 91, "U": 92,
    }

    # Try 2-letter then 1-letter element symbols
    for length in [2, 1]:
        if len(label) >= length:
            prefix = label[:length]
            if prefix in valid_elements:
                return valid_elements[prefix]

    return 6  # Default to carbon
