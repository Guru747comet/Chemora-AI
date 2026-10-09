from __future__ import annotations
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.molecule import analyze_smiles
from app.services.pdf_ingest import extract_pdf, PDFProcessingError
from app.services.report_pdf import create_analysis_report

BASE_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
REPORT_DIR = STORAGE_DIR / "reports"
STATIC_DIR = BASE_DIR / "app" / "static"
DB_PATH = STORAGE_DIR / "chemora.sqlite3"
MAX_PDF_BYTES = int(os.getenv("CHEMORA_MAX_PDF_BYTES", str(15 * 1024 * 1024)))
for path in (UPLOAD_DIR, REPORT_DIR):
    path.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Chemora-AI API",
    description="Prototype API for disease PDF extraction and RDKit-based molecular analysis.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with connect_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS disease_reports (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            page_count INTEGER NOT NULL,
            extracted_text TEXT NOT NULL,
            hints_json TEXT NOT NULL,
            confirmed_disease_name TEXT,
            confirmed_targets_json TEXT NOT NULL DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            report_id TEXT,
            molecule_name TEXT,
            smiles TEXT NOT NULL,
            canonical_smiles TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(report_id) REFERENCES disease_reports(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS generated_reports (
            id TEXT PRIMARY KEY,
            analysis_id TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
        );
        """)


# Initialize local SQLite tables during import for both the app and automated tests.
init_db()


class MoleculeRequest(BaseModel):
    smiles: str = Field(min_length=1, max_length=4000)
    molecule_name: Optional[str] = Field(default=None, max_length=200)
    disease_report_id: Optional[str] = None


class DiseaseConfirmRequest(BaseModel):
    disease_name: Optional[str] = Field(default=None, max_length=200)
    targets: list[str] = Field(default_factory=list, max_length=20)


class GenerateReportRequest(BaseModel):
    analysis_id: str


@app.get("/", include_in_schema=False)
def home():
    """Serve the no-build fallback UI; the React frontend is optional."""
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Chemora-AI", "version": app.version, "rdkit": _rdkit_version()}


def _rdkit_version():
    try:
        from rdkit import rdBase
        return rdBase.rdkitVersion
    except Exception:
        return "unavailable"


@app.post("/api/disease-reports/upload")
async def upload_disease_pdf(file: UploadFile = File(...)):
    filename = Path(file.filename or "disease-report.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are accepted.")
    data = await file.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail=f"PDF exceeds the {MAX_PDF_BYTES // (1024 * 1024)} MB size limit.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=415, detail="The uploaded file does not appear to be a valid PDF.")
    try:
        extracted = extract_pdf(data)
    except PDFProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    report_id = str(uuid.uuid4())[:8].upper()
    stored_filename = f"{report_id}_{uuid.uuid4().hex}.pdf"
    (UPLOAD_DIR / stored_filename).write_bytes(data)
    uploaded_at = datetime.now(timezone.utc).isoformat()
    with connect_db() as conn:
        conn.execute(
            "INSERT INTO disease_reports (id, filename, stored_filename, uploaded_at, page_count, extracted_text, hints_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (report_id, filename, stored_filename, uploaded_at, extracted["page_count"], extracted["text"], json.dumps(extracted["summary"])),
        )
    return {
        "id": report_id, "filename": filename, "uploaded_at": uploaded_at,
        "page_count": extracted["page_count"], "hints": extracted["summary"],
        "text_preview": extracted["text"][:5000], "text_characters": len(extracted["text"]),
        "status": "extracted - review required",
    }


@app.get("/api/disease-reports")
def list_disease_reports():
    with connect_db() as conn:
        rows = conn.execute("SELECT id, filename, uploaded_at, page_count, confirmed_disease_name FROM disease_reports ORDER BY uploaded_at DESC LIMIT 100").fetchall()
    return [dict(row) for row in rows]


@app.get("/api/disease-reports/{report_id}")
def get_disease_report(report_id: str):
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM disease_reports WHERE id = ?", (report_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Disease report not found.")
    record = dict(row)
    return {
        "id": record["id"], "filename": record["filename"], "uploaded_at": record["uploaded_at"],
        "page_count": record["page_count"], "text_preview": record["extracted_text"][:8000],
        "hints": json.loads(record["hints_json"]), "disease_name": record["confirmed_disease_name"],
        "targets": json.loads(record["confirmed_targets_json"]),
    }


@app.put("/api/disease-reports/{report_id}/confirm")
def confirm_disease_report(report_id: str, payload: DiseaseConfirmRequest):
    targets = [target.strip()[:150] for target in payload.targets if target.strip()]
    with connect_db() as conn:
        exists = conn.execute("SELECT id FROM disease_reports WHERE id = ?", (report_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Disease report not found.")
        conn.execute(
            "UPDATE disease_reports SET confirmed_disease_name = ?, confirmed_targets_json = ? WHERE id = ?",
            (payload.disease_name.strip() if payload.disease_name else None, json.dumps(targets), report_id),
        )
    return {"status": "saved", "report_id": report_id, "disease_name": payload.disease_name, "targets": targets}


@app.post("/api/molecules/analyze")
def analyze_molecule(payload: MoleculeRequest):
    if payload.disease_report_id:
        with connect_db() as conn:
            exists = conn.execute("SELECT id FROM disease_reports WHERE id = ?", (payload.disease_report_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Linked disease report was not found.")
    try:
        result = analyze_smiles(payload.smiles)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    analysis_id = str(uuid.uuid4())[:8].upper()
    created_at = datetime.now(timezone.utc).isoformat()
    with connect_db() as conn:
        conn.execute(
            "INSERT INTO analyses (id, report_id, molecule_name, smiles, canonical_smiles, result_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (analysis_id, payload.disease_report_id, payload.molecule_name, payload.smiles.strip(), result["canonical_smiles"], json.dumps(result), created_at),
        )
    return {
        "id": analysis_id, "molecule_name": payload.molecule_name, "smiles": payload.smiles,
        "disease_report_id": payload.disease_report_id, "created_at": created_at, "result": result,
        "docking_status": "not implemented in this starter version",
        "admet_status": "not implemented in this starter version",
        "generation_status": "molecular generation not implemented in this starter version",
    }


@app.get("/api/history")
def get_history():
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT a.id, a.molecule_name, a.smiles, a.canonical_smiles, a.created_at,
                   a.report_id, r.filename AS disease_filename
            FROM analyses a LEFT JOIN disease_reports r ON a.report_id = r.id
            ORDER BY a.created_at DESC LIMIT 100
        """).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/history/{analysis_id}")
def get_analysis(analysis_id: str):
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    result = dict(row)
    result["result"] = json.loads(result.pop("result_json"))
    return result


@app.post("/api/reports/generate")
def generate_report(payload: GenerateReportRequest):
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (payload.analysis_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Analysis not found.")
        analysis = dict(row)
        disease = None
        if analysis["report_id"]:
            r = conn.execute("SELECT filename, confirmed_disease_name, confirmed_targets_json FROM disease_reports WHERE id = ?", (analysis["report_id"],)).fetchone()
            disease = dict(r) if r else None
    analysis["result"] = json.loads(analysis.pop("result_json"))
    report_id = str(uuid.uuid4())[:8].upper()
    stored_filename = f"ChemoraAI_Drug_Discovery_Report_{report_id}.pdf"
    destination = REPORT_DIR / stored_filename
    create_analysis_report(destination, analysis, disease)
    created_at = datetime.now(timezone.utc).isoformat()
    with connect_db() as conn:
        conn.execute("INSERT INTO generated_reports (id, analysis_id, stored_filename, created_at) VALUES (?, ?, ?, ?)", (report_id, payload.analysis_id, stored_filename, created_at))
    return {"id": report_id, "analysis_id": payload.analysis_id, "filename": stored_filename, "created_at": created_at, "download_url": f"/api/reports/{report_id}/download"}


@app.get("/api/reports")
def list_generated_reports():
    with connect_db() as conn:
        rows = conn.execute("""
            SELECT g.id, g.analysis_id, g.stored_filename AS filename, g.created_at,
                   a.molecule_name, a.report_id AS disease_report_id
            FROM generated_reports g
            JOIN analyses a ON a.id = g.analysis_id
            ORDER BY g.created_at DESC LIMIT 100
        """).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/reports/{report_id}/download")
def download_report(report_id: str):
    with connect_db() as conn:
        row = conn.execute("SELECT stored_filename FROM generated_reports WHERE id = ?", (report_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Generated report not found.")
    path = REPORT_DIR / row["stored_filename"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file is missing from storage.")
    return FileResponse(path, media_type="application/pdf", filename=row["stored_filename"])


@app.delete("/api/history/{analysis_id}")
def delete_analysis(analysis_id: str):
    with connect_db() as conn:
        row = conn.execute("SELECT id FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Analysis not found.")
        conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    return {"status": "deleted", "analysis_id": analysis_id}
