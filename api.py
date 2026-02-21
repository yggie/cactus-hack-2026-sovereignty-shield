"""FastAPI backend for the Confidential Document Analyst."""

import os
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from hybrid import generate_hybrid, routing_history
from db import (
    create_case, list_cases, get_case, update_case, delete_case,
    add_file, get_file_path, list_findings, clear_findings,
)
from models import Case, CaseFile, Finding, Report
from parsers import extract_pdf_text, parse_file
from analyzer import analyze_case, get_progress
from report import generate_report

app = FastAPI(title="Confidential Document Analyst API")


# --- Request / Response models ---

class HybridRequest(BaseModel):
    prompt: str
    tools: list[dict] | None = None


class HybridResponse(BaseModel):
    function_calls: list[dict]
    source: str
    confidence: float
    total_time: float


class CreateCaseRequest(BaseModel):
    name: str


class UpdateCaseRequest(BaseModel):
    name: str | None = None
    cloud_consent: bool | None = None


class HealthResponse(BaseModel):
    status: str
    models: dict[str, str]


class AnalysisProgress(BaseModel):
    total: int
    completed: int
    status: str


class AnalysisStartedResponse(BaseModel):
    status: str
    case_id: str


class DeleteResponse(BaseModel):
    ok: bool


# --- Existing endpoints (backward-compatible) ---

@app.post("/api/hybrid", response_model=HybridResponse)
async def hybrid_endpoint(req: HybridRequest):
    messages = [{"role": "user", "content": req.prompt}]
    result = generate_hybrid(messages, req.tools)
    return result


@app.get("/api/health", response_model=HealthResponse)
async def health():
    return {
        "status": "ok",
        "models": {
            "local": "functiongemma-270m (mock)",
            "cloud": "gemini-2.0-flash (mock)",
        },
    }


@app.get("/api/history")
async def history():
    return {"history": routing_history}


# --- Cases CRUD ---

@app.post("/api/cases", response_model=Case)
async def create_case_endpoint(req: CreateCaseRequest):
    return create_case(req.name)


@app.get("/api/cases", response_model=list[Case])
async def list_cases_endpoint():
    return list_cases()


@app.get("/api/cases/{case_id}", response_model=Case)
async def get_case_endpoint(case_id: str):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@app.patch("/api/cases/{case_id}", response_model=Case)
async def update_case_endpoint(case_id: str, req: UpdateCaseRequest):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    case = update_case(case_id, **updates)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@app.delete("/api/cases/{case_id}", response_model=DeleteResponse)
async def delete_case_endpoint(case_id: str):
    if not delete_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return {"ok": True}


# --- File upload ---

@app.post("/api/cases/{case_id}/files", response_model=CaseFile)
async def upload_file_endpoint(case_id: str, file: UploadFile = File(...)):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    content = await file.read()
    filename = file.filename or "unknown.txt"

    # For PDFs, write to a temp file and extract text via pypdf
    if filename.lower().endswith(".pdf"):
        import tempfile, pathlib
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = pathlib.Path(tmp.name)
        try:
            text = extract_pdf_text(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
    else:
        text = content.decode("utf-8", errors="replace")

    fmt, messages = parse_file(text, filename)

    # Store file metadata in DB
    preview = ""
    if messages:
        preview = f"{messages[0].sender}: {messages[0].text[:100]}"

    cf = add_file(
        case_id=case_id,
        filename=filename,
        fmt=fmt,
        message_count=len(messages),
        preview=preview,
    )

    # Save raw file to disk
    dest = get_file_path(cf.id)
    dest.write_text(text, encoding="utf-8")

    return cf


@app.get("/api/cases/{case_id}/files", response_model=list[CaseFile])
async def list_files_endpoint(case_id: str):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case.files


# --- Analysis ---

@app.post("/api/cases/{case_id}/analyze", response_model=AnalysisStartedResponse)
async def analyze_endpoint(case_id: str, bg: BackgroundTasks):
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not case.files:
        raise HTTPException(status_code=400, detail="No files to analyze")

    bg.add_task(analyze_case, case_id)
    return {"status": "started", "case_id": case_id}


@app.get("/api/cases/{case_id}/progress", response_model=AnalysisProgress)
async def progress_endpoint(case_id: str):
    return get_progress(case_id)


# --- Findings ---

@app.get("/api/cases/{case_id}/findings", response_model=list[Finding])
async def findings_endpoint(case_id: str):
    return list_findings(case_id)


# --- Report ---

@app.get("/api/cases/{case_id}/report", response_model=Report)
async def report_endpoint(case_id: str):
    try:
        report = generate_report(case_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return report


@app.get("/api/cases/{case_id}/report/export")
async def export_report_endpoint(case_id: str):
    try:
        report = generate_report(case_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PlainTextResponse(
        content=report.markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=report-{case_id}.md"},
    )


# --- Static file serving for production ---

DIST_DIR = Path(__file__).parent / "frontend" / "dist"

if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        """Serve index.html for all non-API routes (SPA client-side routing)."""
        file_path = DIST_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST_DIR / "index.html")
