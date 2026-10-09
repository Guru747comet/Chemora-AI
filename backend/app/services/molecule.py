"""RDKit-backed molecular descriptor calculation."""
from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski, rdMolDescriptors


def analyze_smiles(smiles: str) -> dict:
    if not smiles or not smiles.strip():
        raise ValueError("Please enter a SMILES string.")

    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None:
        raise ValueError("RDKit could not parse this SMILES string. Check the chemical notation and try again.")

    canonical_smiles = Chem.MolToSmiles(mol)
    descriptors = {
        "molecular_formula": rdMolDescriptors.CalcMolFormula(mol),
        "molecular_weight_da": round(float(Descriptors.MolWt(mol)), 3),
        "logp": round(float(Descriptors.MolLogP(mol)), 3),
        "h_bond_donors": int(Lipinski.NumHDonors(mol)),
        "h_bond_acceptors": int(Lipinski.NumHAcceptors(mol)),
        "rotatable_bonds": int(Lipinski.NumRotatableBonds(mol)),
        "tpsa_a2": round(float(Descriptors.TPSA(mol)), 3),
        "heavy_atom_count": int(mol.GetNumHeavyAtoms()),
    }
    criteria = [
        ("Molecular weight <= 500 Da", descriptors["molecular_weight_da"] <= 500),
        ("LogP <= 5", descriptors["logp"] <= 5),
        ("Hydrogen bond donors <= 5", descriptors["h_bond_donors"] <= 5),
        ("Hydrogen bond acceptors <= 10", descriptors["h_bond_acceptors"] <= 10),
    ]
    violations = sum(not passed for _, passed in criteria)
    return {
        "canonical_smiles": canonical_smiles,
        "descriptors": descriptors,
        "lipinski": {
            "criteria": [{"criterion": label, "passed": passed} for label, passed in criteria],
            "violations": violations,
            "passes_rule_of_five_heuristic": violations <= 1,
            "interpretation": "A heuristic only; it does not establish efficacy, safety, or clinical suitability.",
        },
        "molecular_structure_svg": _molecule_svg(mol),
        "method": "RDKit descriptor calculation",
    }


def _molecule_svg(mol) -> str:
    """Return a small SVG sketch for rendering in the web UI."""
    try:
        from rdkit.Chem.Draw import rdMolDraw2D
        drawer = rdMolDraw2D.MolDraw2DSVG(360, 210)
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        return drawer.GetDrawingText()
    except Exception:
        return ""
