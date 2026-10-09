import io
import os
import sys
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app

client = TestClient(app)


def make_pdf(text="Disease Research Brief\nDisease: Demonstration condition\nThis is a test-only PDF."):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_home_serves_fallback_ui():
    response = client.get("/")
    assert response.status_code == 200
    assert "Chemora-AI" in response.text


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_molecule_analysis_aspirin():
    response = client.post("/api/molecules/analyze", json={
        "molecule_name": "Aspirin",
        "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["result"]["descriptors"]["molecular_formula"] == "C9H8O4"
    assert payload["result"]["descriptors"]["molecular_weight_da"] > 180
    assert payload["result"]["lipinski"]["violations"] == 0


def test_invalid_smiles_returns_422():
    response = client.post("/api/molecules/analyze", json={"smiles": "this-is-not-smiles"})
    assert response.status_code == 422


def test_pdf_upload_and_confirm():
    content = make_pdf("Disease Research Brief\nDisease: Demonstration condition\nProtein ABC1 appears in this test text.")
    response = client.post("/api/disease-reports/upload", files={"file": ("test_brief.pdf", content, "application/pdf")})
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["page_count"] == 1
    assert "Demonstration condition" in report["text_preview"]
    confirm = client.put(f"/api/disease-reports/{report['id']}/confirm", json={"disease_name": "Demonstration condition", "targets": ["ABC1"]})
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "saved"


def test_reject_non_pdf():
    response = client.post("/api/disease-reports/upload", files={"file": ("not.pdf", b"not a pdf", "application/pdf")})
    assert response.status_code == 415


def test_generate_and_download_report():
    response = client.post("/api/molecules/analyze", json={"molecule_name": "Aspirin", "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"})
    assert response.status_code == 200, response.text
    analysis_id = response.json()["id"]
    generated = client.post("/api/reports/generate", json={"analysis_id": analysis_id})
    assert generated.status_code == 200, generated.text
    download = client.get(generated.json()["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/pdf")
    assert download.content.startswith(b"%PDF")
