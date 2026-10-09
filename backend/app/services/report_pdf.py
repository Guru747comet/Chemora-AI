"""Generate per-molecule PDF analysis reports."""
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

NAVY = colors.HexColor("#10243A")
TEAL = colors.HexColor("#0E9384")
MUTED = colors.HexColor("#526477")
PALE = colors.HexColor("#EDF7F6")


def create_analysis_report(destination: Path, analysis: dict, disease_report: dict | None = None) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(destination), pagesize=A4,
        rightMargin=19*mm, leftMargin=19*mm, topMargin=20*mm, bottomMargin=18*mm,
        title="Chemora-AI Molecular Analysis Report", author="Chemora-AI prototype",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=27, leading=32, textColor=NAVY, alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name="SubTitle", parent=styles["Normal"], fontSize=11, leading=16, textColor=MUTED, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading1"], fontSize=16, leading=20, textColor=NAVY, spaceBefore=8, spaceAfter=8, keepWithNext=True))
    styles.add(ParagraphStyle(name="Body2", parent=styles["BodyText"], fontSize=9.2, leading=13.2, textColor=colors.HexColor("#243447"), spaceAfter=6))
    styles.add(ParagraphStyle(name="Small2", parent=styles["BodyText"], fontSize=8, leading=11, textColor=MUTED, spaceAfter=4))
    styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontSize=9, leading=13, textColor=NAVY, backColor=PALE, borderPadding=8, spaceBefore=8, spaceAfter=10))

    desc = analysis["result"]["descriptors"]
    lip = analysis["result"]["lipinski"]
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story = [Spacer(1, 32*mm), Paragraph("CHEMORA-AI", styles["CoverTitle"]), Paragraph("Molecular Analysis Report", styles["SubTitle"]), Spacer(1, 10*mm)]
    story.append(Paragraph("Preliminary computational screening of a candidate molecule", styles["SubTitle"]))
    story += [Spacer(1, 22*mm)]
    meta = [
        ["Report ID", escape(analysis["id"])],
        ["Generated", generated],
        ["Molecule", escape(analysis.get("molecule_name") or "Unnamed molecule")],
        ["Analysis method", "RDKit descriptor calculation"],
        ["Source disease report", escape((disease_report or {}).get("filename") or "Not linked")],
    ]
    table = Table(meta, colWidths=[47*mm, 105*mm], hAlign="CENTER")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), NAVY), ("TEXTCOLOR", (0,0), (0,-1), colors.white),
        ("BACKGROUND", (1,0), (1,-1), colors.HexColor("#F5F8FA")),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#D7E0E8")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story += [table, Spacer(1, 22*mm), Paragraph("Research prototype only. This report is not a drug approval, medical recommendation, or proof of efficacy or safety.", styles["Callout"]), PageBreak()]

    story.append(Paragraph("1. Executive Summary", styles["Section"]))
    story.append(Paragraph(
        "This report presents chemical descriptors calculated from the submitted SMILES using RDKit. "
        "It provides a reproducible starting point for computational screening. No target binding, therapeutic efficacy, clinical safety, "
        "or novelty conclusion is made by this analysis alone.", styles["Body2"]))
    story.append(Paragraph("2. Submitted Molecule", styles["Section"]))
    story.append(Paragraph(f"<b>Name:</b> {escape(analysis.get('molecule_name') or 'Unnamed molecule')}", styles["Body2"]))
    story.append(Paragraph(f"<b>Input SMILES:</b> <font name='Courier'>{escape(analysis['smiles'])}</font>", styles["Body2"]))
    story.append(Paragraph(f"<b>Canonical SMILES:</b> <font name='Courier'>{escape(analysis['result']['canonical_smiles'])}</font>", styles["Body2"]))
    story.append(Paragraph("3. Calculated Molecular Descriptors", styles["Section"]))
    rows = [["Descriptor", "Calculated value"],
            ["Molecular formula", desc["molecular_formula"]],
            ["Molecular weight", f"{desc['molecular_weight_da']} Da"],
            ["LogP", str(desc["logp"])],
            ["Hydrogen bond donors", str(desc["h_bond_donors"])],
            ["Hydrogen bond acceptors", str(desc["h_bond_acceptors"])],
            ["Rotatable bonds", str(desc["rotatable_bonds"])],
            ["Topological polar surface area", f"{desc['tpsa_a2']} A^2"],
            ["Heavy atom count", str(desc["heavy_atom_count"])]]
    desc_table = Table(rows, colWidths=[85*mm, 65*mm], repeatRows=1)
    desc_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.45, colors.HexColor("#D7E0E8")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")]),
        ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(desc_table)
    story.append(Paragraph("4. Lipinski Rule of Five Heuristic", styles["Section"]))
    lip_rows = [["Criterion", "Result"]]
    lip_rows += [[x["criterion"], "Pass" if x["passed"] else "Violation"] for x in lip["criteria"]]
    lip_table = Table(lip_rows, colWidths=[108*mm, 42*mm], repeatRows=1)
    lip_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.45, colors.HexColor("#D7E0E8")), ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")]),
    ]))
    story += [lip_table, Spacer(1, 4*mm)]
    story.append(Paragraph(f"Violations: {lip['violations']}. The Rule of Five screen is a heuristic, not proof that this molecule is an effective or safe drug.", styles["Body2"]))

    story.append(Paragraph("5. Disease Context and Provenance", styles["Section"]))
    if disease_report:
        story.append(Paragraph(f"Uploaded document: {escape(disease_report.get('filename',''))}.", styles["Body2"]))
        story.append(Paragraph("The document's text extraction does not establish a validated target-disease relationship. Any target or disease selection must be checked against the source literature by the user.", styles["Body2"]))
    else:
        story.append(Paragraph("No disease research PDF was linked to this molecule analysis.", styles["Body2"]))
    story.append(Paragraph("6. Analyses Not Performed", styles["Section"]))
    story.append(Paragraph("This report does not contain molecular docking or ADMET model results unless those modules are explicitly configured and run in a future version. This starter prototype does not generate novel chemical structures. No claim of chemical novelty is made.", styles["Body2"]))
    story.append(Paragraph("7. Recommended Next Steps", styles["Section"]))
    story.append(Paragraph("Confirm the scientific target, obtain a suitable protein structure, perform validated preparation, run docking using a configured scientific tool, review evidence for the selected compound, and obtain expert and experimental validation before making biological claims.", styles["Body2"]))
    story.append(Paragraph("8. References", styles["Section"]))
    for ref in [
        "RDKit documentation: https://www.rdkit.org/docs/",
        "PubChem PUG REST documentation: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest",
        "RCSB Protein Data Bank: https://www.rcsb.org/",
        "AutoDock Vina documentation (future integration): https://autodock-vina.readthedocs.io/",
    ]:
        story.append(Paragraph(escape(ref), styles["Small2"]))
    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return destination


def _page_footer(canvas, doc):
    canvas.saveState()
    w, _ = A4
    canvas.setStrokeColor(colors.HexColor("#DCE4EA"))
    canvas.line(19*mm, 14*mm, w-19*mm, 14*mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(19*mm, 9*mm, "Chemora-AI | Preliminary computational research")
    canvas.drawRightString(w-19*mm, 9*mm, f"Page {doc.page}")
    canvas.restoreState()
