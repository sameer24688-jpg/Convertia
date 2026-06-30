"""
Unit tests for coordinate/geometry helpers and property namespacing in the
CDXML parser.

Run from the repository root:
    python -m unittest discover tests
"""
import unittest
import xml.etree.ElementTree as ET

from sdf_csv_converter import cdx_parser as p


class TestParsePoint(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(p._parse_point("1 2"), (1.0, 2.0))
        self.assertEqual(p._parse_point("3.5 -4.25"), (3.5, -4.25))

    def test_extra_tokens_use_first_two(self):
        self.assertEqual(p._parse_point("1 2 3"), (1.0, 2.0))

    def test_invalid(self):
        self.assertIsNone(p._parse_point(""))
        self.assertIsNone(p._parse_point("1"))
        self.assertIsNone(p._parse_point("a b"))


class TestBboxCenter(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(p._bbox_center("0 0 10 20"), (5.0, 10.0))
        self.assertEqual(p._bbox_center("2 4 6 8"), (4.0, 6.0))

    def test_invalid(self):
        self.assertIsNone(p._bbox_center(""))
        self.assertIsNone(p._bbox_center("0 0 10"))
        self.assertIsNone(p._bbox_center("a b c d"))


class TestNearestIndex(unittest.TestCase):
    def setUp(self):
        self.centers = [(0.0, 0.0), (10.0, 10.0), (100.0, 0.0)]

    def test_picks_closest(self):
        self.assertEqual(p._nearest_index(self.centers, (1.0, 1.0)), 0)
        self.assertEqual(p._nearest_index(self.centers, (9.0, 9.0)), 1)
        self.assertEqual(p._nearest_index(self.centers, (101.0, 1.0)), 2)

    def test_none_point_falls_back_to_zero(self):
        self.assertEqual(p._nearest_index(self.centers, None), 0)

    def test_skips_none_centers(self):
        centers = [None, (10.0, 10.0), None]
        self.assertEqual(p._nearest_index(centers, (9.0, 9.0)), 1)

    def test_empty_centers_returns_zero(self):
        self.assertEqual(p._nearest_index([], (1.0, 1.0)), 0)


class TestTextString(unittest.TestCase):
    def test_concatenates_runs(self):
        t = ET.fromstring('<t><s>Hello </s><s>World</s></t>')
        self.assertEqual(p._text_string(t), "Hello World")

    def test_strips(self):
        t = ET.fromstring('<t><s>  spaced  </s></t>')
        self.assertEqual(p._text_string(t), "spaced")

    def test_empty(self):
        t = ET.fromstring('<t></t>')
        self.assertEqual(p._text_string(t), "")


class TestDetectCompoundId(unittest.TestCase):
    def test_underscore_code(self):
        self.assertEqual(p._detect_compound_id(["Series A", "PROJ-42\n001"]), "PROJ-42")

    def test_hyphen_code(self):
        self.assertEqual(p._detect_compound_id(["LAB-059"]), "LAB-059")

    def test_no_match_for_plain_words(self):
        self.assertEqual(p._detect_compound_id(["Series A", "Series B"]), "")

    def test_empty(self):
        self.assertEqual(p._detect_compound_id([]), "")


class TestPropertiesDictNamespacing(unittest.TestCase):
    def test_chemdraw_prefix_and_template_filtering(self):
        s = p.CDXStructure(
            xml_index=3,
            title="Compound A",
            compound_id="PROJ-42",
            chem_props={
                "MolecularWeight": "Molecular Weight: ",  # empty template -> dropped
                "LogP": "Log P: 3.2",                      # real value -> kept
                "ExactMass": "Exact Mass:",                # template -> dropped
                "Name": "",                                 # empty -> dropped
            },
        )
        s.annotations = ["Series A", "PROJ-42"]
        props = p.structure_to_properties_dict(s)

        self.assertEqual(props["XmlIndex"], "3")
        self.assertEqual(props["Title"], "Compound A")
        self.assertEqual(props["CompoundID"], "PROJ-42")
        self.assertEqual(props["Annotations"], "Series A | PROJ-42")

        # ChemDraw values are namespaced and never collide with RDKit columns.
        self.assertEqual(props["ChemDraw_LogP"], "Log P: 3.2")
        self.assertNotIn("ChemDraw_MolecularWeight", props)
        self.assertNotIn("ChemDraw_ExactMass", props)
        self.assertNotIn("MolecularWeight", props)  # reserved for RDKit
        self.assertNotIn("Name", props)


if __name__ == "__main__":
    unittest.main()
