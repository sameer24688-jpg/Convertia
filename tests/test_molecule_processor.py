"""
Unit tests for RDKit property computation.

Run from the repository root:
    python -m unittest discover tests
"""
import unittest

from rdkit import Chem

from sdf_csv_converter import molecule_processor as mp
from sdf_csv_converter.clogp import calc_clogp


class TestCLogP(unittest.TestCase):
    def test_differs_from_crippen_logp(self):
        """CLogP uses JPLogP, not Wildman-Crippen MolLogP."""
        from rdkit.Chem import Crippen

        mol = Chem.MolFromSmiles("CC(=O)O")
        crippen = Crippen.MolLogP(mol)
        clogp = calc_clogp(mol)
        self.assertNotAlmostEqual(clogp, crippen, places=2)

    def test_clogp_in_compute_properties(self):
        mol = Chem.MolFromSmiles("c1ccc(O)cc1")
        props = mp.compute_properties(mol)
        self.assertIn("CLogP", props)
        self.assertTrue(props["CLogP"])
        self.assertAlmostEqual(float(props["CLogP"]), calc_clogp(mol), places=3)

    def test_invalid_molecule_returns_empty_clogp(self):
        props = mp.compute_properties(None)
        self.assertEqual(props, {})


class TestStereoCenters(unittest.TestCase):
    def test_chiral_center_counted(self):
        mol = Chem.MolFromSmiles("C[C@H](O)N")
        props = mp.compute_properties(mol)
        self.assertEqual(props["NumStereoCenters"], "1")

    def test_achiral_molecule_is_zero(self):
        mol = Chem.MolFromSmiles("CCO")
        props = mp.compute_properties(mol)
        self.assertEqual(props["NumStereoCenters"], "0")

    def test_two_stereocenters(self):
        mol = Chem.MolFromSmiles("C[C@H](O)[C@H](N)C")
        props = mp.compute_properties(mol)
        self.assertEqual(props["NumStereoCenters"], "2")


if __name__ == "__main__":
    unittest.main()
