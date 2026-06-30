"""
Unit tests for nickname / abbreviation / R-group expansion in the CDXML parser.

Covers:
- Pure detection helpers (no RDKit needed).
- Embedded-fragment expansion for OMe / Ph / Boc against synthetic fixtures
  modeled on ChemDraw's real serialization.
- R-groups becoming RDKit dummy atoms with atom-map numbers.
- Graceful fallback for multi-attachment nicknames.

Run from the repository root:
    python -m unittest discover tests
"""
import os
import unittest
import xml.etree.ElementTree as ET

from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

from sdf_csv_converter import cdx_parser as p

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _only_structure(fixture_name):
    """Parse a fixture and return its single CDXStructure."""
    path = os.path.join(FIXTURES, fixture_name)
    structures = list(p.parse_cdx_or_cdxml(path))
    assert len(structures) == 1, f"{fixture_name}: expected 1 structure"
    return structures[0]


class TestNicknameFragmentHelper(unittest.TestCase):
    def test_returns_embedded_fragment(self):
        n = ET.fromstring(
            '<n id="2" NodeType="Nickname">'
            '<fragment id="200"><n id="201"/></fragment>'
            "<t><s>OMe</s></t></n>"
        )
        frag = p._nickname_fragment(n)
        self.assertIsNotNone(frag)
        self.assertEqual(p._local_tag(frag.tag), "fragment")

    def test_none_when_no_embedded_fragment(self):
        n = ET.fromstring('<n id="1" Element="6"/>')
        self.assertIsNone(p._nickname_fragment(n))


class TestExternalConnectionPointHelper(unittest.TestCase):
    def test_true_for_ecp(self):
        n = ET.fromstring(
            '<n id="9" NodeType="ExternalConnectionPoint" '
            'ExternalConnectionNum="1"/>'
        )
        self.assertTrue(p._is_external_connection_point(n))

    def test_false_for_plain_atom(self):
        self.assertFalse(
            p._is_external_connection_point(ET.fromstring('<n id="1"/>'))
        )

    def test_false_for_generic_nickname(self):
        n = ET.fromstring('<n id="7" NodeType="GenericNickname"/>')
        self.assertFalse(p._is_external_connection_point(n))


class TestRGroupMapNumber(unittest.TestCase):
    def test_numbered_rgroups(self):
        self.assertEqual(p._rgroup_map_number("R1"), 1)
        self.assertEqual(p._rgroup_map_number("R2"), 2)
        self.assertEqual(p._rgroup_map_number("R12"), 12)

    def test_generic_placeholders_map_to_zero(self):
        self.assertEqual(p._rgroup_map_number("R"), 0)
        self.assertEqual(p._rgroup_map_number("X"), 0)
        self.assertEqual(p._rgroup_map_number("Y"), 0)
        self.assertEqual(p._rgroup_map_number("Z"), 0)

    def test_non_rgroup_labels_return_none(self):
        for label in ("OH", "N", "Me", "OMe", "Ph", "", "  ", "RA", "1R"):
            self.assertIsNone(
                p._rgroup_map_number(label), f"{label!r} should not be an R-group"
            )

    def test_whitespace_is_stripped(self):
        self.assertEqual(p._rgroup_map_number("  R3  "), 3)


class TestExpansionFixtures(unittest.TestCase):
    """Embedded single-attachment nicknames expand to correct chemistry."""

    def test_ome_expands_to_dimethyl_ether(self):
        s = _only_structure("nickname_ome.cdxml")
        self.assertIsNotNone(s.mol)
        self.assertEqual(rdMolDescriptors.CalcMolFormula(s.mol), "C2H6O")
        # Attachment was rewired onto the oxygen: it bridges both methyls.
        oxygens = [a for a in s.mol.GetAtoms() if a.GetAtomicNum() == 8]
        self.assertEqual(len(oxygens), 1)
        self.assertEqual(oxygens[0].GetDegree(), 2)

    def test_ph_expands_to_aromatic_ring(self):
        s = _only_structure("nickname_ph.cdxml")
        self.assertIsNotNone(s.mol)
        self.assertEqual(rdMolDescriptors.CalcMolFormula(s.mol), "C7H8")
        aromatic = [a for a in s.mol.GetAtoms() if a.GetIsAromatic()]
        self.assertEqual(len(aromatic), 6)
        self.assertEqual(rdMolDescriptors.CalcNumRings(s.mol), 1)

    def test_boc_expands_to_correct_formula(self):
        s = _only_structure("nickname_boc.cdxml")
        self.assertIsNotNone(s.mol)
        self.assertEqual(rdMolDescriptors.CalcMolFormula(s.mol), "C6H12O2")

    def test_ecp_atom_is_removed(self):
        # An ExternalConnectionPoint must never survive into the built molecule.
        for fixture, n_heavy in (
            ("nickname_ome.cdxml", 3),
            ("nickname_ph.cdxml", 7),
        ):
            s = _only_structure(fixture)
            self.assertEqual(s.mol.GetNumAtoms(), n_heavy, fixture)
            # No dummy/placeholder atoms left behind from the ECP.
            self.assertFalse(
                any(a.GetAtomicNum() == 0 for a in s.mol.GetAtoms()), fixture
            )


class TestRGroupExpansion(unittest.TestCase):
    def test_rgroups_become_mapped_dummy_atoms(self):
        s = _only_structure("rgroup_r1r2.cdxml")
        self.assertIsNotNone(s.mol)
        dummies = [a for a in s.mol.GetAtoms() if a.GetAtomicNum() == 0]
        self.assertEqual(len(dummies), 2)
        map_nums = sorted(a.GetAtomMapNum() for a in dummies)
        self.assertEqual(map_nums, [1, 2])
        # Canonical SMILES surfaces the mapped attachment points.
        smiles = Chem.MolToSmiles(s.mol)
        self.assertIn("[*:1]", smiles)
        self.assertIn("[*:2]", smiles)


class TestMultiAttachFallback(unittest.TestCase):
    def test_multi_attachment_falls_back_to_single_atom(self):
        # 2+ ExternalConnectionPoints is out of scope: the nickname must collapse
        # to a single atom (not expand) and conversion must not raise.
        s = _only_structure("multi_attach.cdxml")
        self.assertIsNotNone(s.mol)
        # 2 core carbons + 1 collapsed nickname atom = 3 heavy atoms.
        # (Full expansion of the -O-CH2-O- bridge would yield 5.)
        self.assertEqual(s.mol.GetNumAtoms(), 3)


if __name__ == "__main__":
    unittest.main()
