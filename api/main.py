"""
FastAPI server — Wires the three agents (Extractor → Validator → Router)
with storage and query capabilities. Serves the UI.

Endpoints:
  POST /api/process    — Upload a document, run the full pipeline
  GET  /api/shipments  — List all processed shipments
  GET  /api/shipments/{id} — Get a single shipment with full details
  POST /api/query      — Ask a natural-language question over stored data
  GET  /               — Serve the UI
"""

import json
import os
import sys
import shutil
import traceback
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.extractor import extract_fields
from agents.validator import validate
from agents.router import route
from storage.database import store_result, get_all_shipments, get_shipment
from storage.query_engine import ask

app = FastAPI(title="Nova Trade Document Pipeline", version="1.0.0")

# Directory for uploaded files
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Default rules path
RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "rules", "customer_rules.json")

# ── UI ──────────────────────────────────────────────────────────────

UI_DIR = os.path.join(os.path.dirname(__file__), "..", "ui")


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the main UI page."""
    index_path = os.path.join(UI_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>UI not found. Place index.html in /ui directory.</h1>")


@app.get("/style.css")
async def serve_css():
    return FileResponse(os.path.join(UI_DIR, "style.css"), media_type="text/css")


@app.get("/app.js")
async def serve_js():
    return FileResponse(os.path.join(UI_DIR, "app.js"), media_type="application/javascript")


# ── Pipeline API ────────────────────────────────────────────────────

@app.post("/api/process")
async def process_document(file: UploadFile = File(...)):
    """
    Run the full pipeline on an uploaded document:
    1. Save the file
    2. Extract fields (Extractor Agent)
    3. Validate against rules (Validator Agent)
    4. Route decision (Router Agent)
    5. Store result

    Returns the complete pipeline output.
    """
    # Save uploaded file
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        MOCK_MODE = False  # Set to True to run offline without API key

        if MOCK_MODE:
            is_messy = "messy" in file.filename.lower()
            
            # Mock Extraction
            extraction = {
                "document_type": {"value": "Bill of Lading", "confidence": 0.95},
                "document_reference": {"value": "DOC-1234", "confidence": 0.95},
                "consignee_name": {"value": "Nordic Imports ApS" if is_messy else "TechWorld Distribution GmbH", "confidence": 0.90 if is_messy else 0.98},
                "hs_code": {"value": "6204.62" if is_messy else "8528.72", "confidence": 0.98},
                "port_of_loading": {"value": "Nansha, Guangzhou" if is_messy else "Yantian, Shenzhen", "confidence": 0.95},
                "port_of_discharge": {"value": "Aarhus, Denmark" if is_messy else "Hamburg, Germany", "confidence": 0.98},
                "incoterms": {"value": None if is_messy else "CIF Hamburg", "confidence": 0.0 if is_messy else 0.95},
                "description_of_goods": {"value": "Cotton Trousers" if is_messy else "LED Display Panels", "confidence": 0.95},
                "gross_weight": {"value": "2,100.00 KGS" if is_messy else "4,250.00 KGS", "confidence": 0.95},
                "invoice_number": {"value": None if is_messy else "SBE-INV-2024-1547", "confidence": 0.0 if is_messy else 0.9}
            }
            
            # Real validation (it doesn't use the LLM, it uses rules)
            validation = validate(extraction, RULES_PATH)
            
            # Mock Routing
            if is_messy:
                routing = {
                    "decision": "amendment_required",
                    "reasoning": "Mismatches found in Consignee Name, HS Code, and missing Incoterms.",
                    "draft_email": "Dear Supplier,\n\nPlease amend the following fields on the document:\n- Consignee Name: Found 'Nordic Imports ApS', expected 'TechWorld Distribution GmbH'\n- HS Code: Found '6204.62', expected '8528.72'\n- Incoterms: Missing, expected 'CIF Hamburg'\n\nPlease send the revised document.\n\nBest regards,\nCG Team"
                }
            else:
                routing = {
                    "decision": "auto_approve",
                    "reasoning": "All required fields matched perfectly with high confidence.",
                    "draft_email": None
                }
        else:
            # Step 1: Extract
            extraction = extract_fields(file_path)
            if "_error" in extraction:
                raise HTTPException(
                    status_code=422,
                    detail=f"Extraction failed: {extraction['_error']}"
                )

            # Step 2: Validate
            validation = validate(extraction, RULES_PATH)

            # Step 3: Route
            routing = route(validation)

        # Step 4: Store
        shipment_id = store_result(extraction, validation, routing)

        return {
            "shipment_id": shipment_id,
            "file_name": file.filename,
            "extraction": extraction,
            "validation": validation,
            "routing": routing,
            "pipeline_status": "complete",
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline error: {str(e)}"
        )


# ── Data API ────────────────────────────────────────────────────────

@app.get("/api/shipments")
async def list_shipments():
    """List all processed shipments."""
    shipments = get_all_shipments()
    # Return summary view (without full JSON blobs)
    summaries = []
    for s in shipments:
        summaries.append({
            "id": s["id"],
            "file_name": s["file_name"],
            "document_type": s["document_type"],
            "consignee_name": s["consignee_name"],
            "customer_name": s["customer_name"],
            "overall_status": s["overall_status"],
            "decision": s["decision"],
            "matches": s["matches"],
            "mismatches": s["mismatches"],
            "uncertain": s["uncertain"],
            "created_at": s["created_at"],
        })
    return {"shipments": summaries}


@app.get("/api/shipments/{shipment_id}")
async def get_shipment_detail(shipment_id: int):
    """Get full details for a single shipment."""
    shipment = get_shipment(shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Parse JSON fields back
    for json_field in ["extraction_json", "validation_json", "routing_json"]:
        if shipment.get(json_field):
            try:
                shipment[json_field] = json.loads(shipment[json_field])
            except json.JSONDecodeError:
                pass

    return shipment


# ── Query API ───────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


@app.post("/api/query")
async def query_data(req: QueryRequest):
    """Answer a natural-language question about stored shipment data."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        # We define MOCK_MODE locally here as well to match the other endpoint
        MOCK_MODE = False
        
        if MOCK_MODE:
            q = req.question.lower()
            if "how many" in q or "count" in q:
                return {"sql": "SELECT COUNT(*) FROM shipments;", "answer": "Based on the database, a total of 2 shipments have been processed so far."}
            elif "mismatch" in q or "review" in q or "amend" in q:
                return {"sql": "SELECT * FROM shipments WHERE decision != 'auto_approve';", "answer": "There is 1 shipment that requires an amendment or review (the messy Bill of Lading)."}
            else:
                return {"sql": "-- Mock query executed", "answer": "In offline demo mode, queries are simulated. I can answer questions like 'How many shipments?' or 'Which had mismatches?'"}
                
        result = ask(req.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")


# ── Health ──────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
