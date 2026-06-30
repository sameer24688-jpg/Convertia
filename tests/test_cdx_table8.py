"""
Integration regression tests for CDXML output correctness. When a proprietary
``Table-8.cdxml`` fixture is present locally at the repository root, these tests
run against it; otherwise they are skipped.

Locks in:
- Page-level text is assigned per-structure (no identical-blob annotations).
- A CompoundID is detected for each plate entry.
- MolecularWeight is a numeric RDKit value (not a ChemDraw label template).
- XmlIndex is monotonic 0..N-1.

Run from the repository root:
    python -m unittest discover tests
"""
import csv
import os
import tempfile
import unittest

from sdf_csv_converter import cdx_parser as p
from sdf_csv_converter import cdx_to_csv
from sdf_csv_converter import stream_utils as su

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE8 = os.path.join(REPO_ROOT, "Table-8.cdxml")


@unittest.skipUnless(os.path.exists(TABLE8), "Table-8.cdxml fixture not found")
class TestTable8Parsing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.structures = list(p.parse_cdx_or_cdxml(TABLE8))

    def test_structure_count(self):
        self.assertEqual(len(self.structures), 15)

    def test_all_have_mols(self):
        self.assertTrue(all(s.mol is not None for s in self.structures))

    def test_annotations_are_distinct_not_blob(self):
        ann_sets = [tuple(s.annotations) for s in self.structures]
        # The pre-fix bug duplicated all page text onto every structure, so all
        # rows were identical. Each structure must now have distinct text.
        self.assertEqual(len(set(ann_sets)), len(ann_sets))

    def test_compound_ids_detected_and_distinct(self):
        ids = [s.compound_id for s in self.structures]
        self.assertTrue(all(ids), "every structure should get a compound id")
        self.assertEqual(len(set(ids)), len(ids), "compound ids must be unique")

    def test_xml_index_monotonic(self):
        self.assertEqual(
            [s.xml_index for s in self.structures],
            list(range(len(self.structures))),
        )

@unittest.skipUnless(os.path.exists(TABLE8), "Table-8.cdxml fixture not found")
class TestTable8CsvOutput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls.csv_path = tempfile.mkstemp(suffix=".csv", prefix="t8_")
        os.close(fd)
        cdx_to_csv.convert_cdx_to_csv(TABLE8, cls.csv_path)
        with open(cls.csv_path, newline="", encoding="utf-8") as f:
            cls.rows = list(csv.DictReader(f))

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.csv_path):
            os.unlink(cls.csv_path)

    def test_molecular_weight_is_numeric(self):
        for row in self.rows:
            mw = row["MolecularWeight"]
            # Must parse as a float (the bug left it as "Molecular Weight: ").
            self.assertGreater(float(mw), 0.0)

    def test_no_chemdraw_template_overwrote_rdkit(self):
        # The ChemDraw template values were empty in this file and must be
        # filtered, so no ChemDraw_MolecularWeight column should appear.
        self.assertNotIn("ChemDraw_MolecularWeight", self.rows[0].keys())

    def test_xml_index_column_monotonic(self):
        indices = [int(row["XmlIndex"]) for row in self.rows]
        self.assertEqual(indices, list(range(len(indices))))

    def test_metadata_columns_come_first(self):
        header = list(self.rows[0].keys())
        self.assertEqual(header[0], "XmlIndex")
        self.assertIn("SMILES", header)
        self.assertLess(header.index("XmlIndex"), header.index("SMILES"))


class TestFieldnameOrdering(unittest.TestCase):
    def test_metadata_then_standard_then_chemdraw(self):
        discovered = {
            "XmlIndex",
            "Title",
            "Annotations",
            "ChemDraw_LogP",
            "SomeSdfTag",
        }
        names = su.build_ordered_fieldnames(discovered, include_standard_properties=True)

        # Metadata first.
        self.assertEqual(names[0], "XmlIndex")
        self.assertLess(names.index("Title"), names.index("SMILES"))
        self.assertLess(names.index("Annotations"), names.index("SMILES"))
        # ChemDraw_* grouped after other discovered props.
        self.assertLess(names.index("SomeSdfTag"), names.index("ChemDraw_LogP"))
        # No duplicates.
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
