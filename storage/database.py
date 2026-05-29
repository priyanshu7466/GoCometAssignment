"""
Storage Layer — SQLite database for storing verified shipment outputs.

Schema stores the full pipeline result: extracted fields, validation results,
routing decision, and timestamps. Queryable via SQL.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "shipments.db")


def _ensure_db():
    """Create the database and tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shipments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            document_type TEXT,
            document_reference TEXT,
            consignee_name TEXT,
            hs_code TEXT,
            port_of_loading TEXT,
            port_of_discharge TEXT,
            incoterms TEXT,
            description_of_goods TEXT,
            gross_weight TEXT,
            invoice_number TEXT,
            customer_name TEXT,
            overall_status TEXT NOT NULL,
            decision TEXT NOT NULL,
            decision_reasoning TEXT,
            draft_email TEXT,
            review_note TEXT,
            total_fields INTEGER,
            matches INTEGER,
            mismatches INTEGER,
            uncertain INTEGER,
            extraction_json TEXT,
            validation_json TEXT,
            routing_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def store_result(extraction: dict, validation: dict, routing: dict) -> int:
    """
    Store the full pipeline result in the database.

    Args:
        extraction: Output from the Extractor Agent.
        validation: Output from the Validator Agent.
        routing: Output from the Router Agent.

    Returns:
        The row ID of the inserted record.
    """
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    now = datetime.utcnow().isoformat()

    # Extract field values safely
    def _val(field_name):
        field = extraction.get(field_name, {})
        if isinstance(field, dict):
            return field.get("value")
        return None

    summary = validation.get("summary", {})

    cursor = conn.execute(
        """
        INSERT INTO shipments (
            file_name, document_type, document_reference,
            consignee_name, hs_code, port_of_loading, port_of_discharge,
            incoterms, description_of_goods, gross_weight, invoice_number,
            customer_name, overall_status, decision, decision_reasoning,
            draft_email, review_note,
            total_fields, matches, mismatches, uncertain,
            extraction_json, validation_json, routing_json,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            extraction.get("_metadata", {}).get("file_name", "unknown"),
            _val("document_type"),
            _val("document_reference"),
            _val("consignee_name"),
            _val("hs_code"),
            _val("port_of_loading"),
            _val("port_of_discharge"),
            _val("incoterms"),
            _val("description_of_goods"),
            _val("gross_weight"),
            _val("invoice_number"),
            validation.get("customer_name", "Unknown"),
            validation.get("overall_status", "unknown"),
            routing.get("decision", "unknown"),
            routing.get("reasoning", ""),
            routing.get("draft_email"),
            routing.get("review_note"),
            summary.get("total_fields", 0),
            summary.get("matches", 0),
            summary.get("mismatches", 0),
            summary.get("uncertain", 0),
            json.dumps(extraction),
            json.dumps(validation),
            json.dumps(routing),
            now,
            now,
        ),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_all_shipments() -> list:
    """Return all shipments as a list of dicts."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM shipments ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_shipment(shipment_id: int) -> dict | None:
    """Return a single shipment by ID."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def execute_query(sql: str) -> list:
    """Execute a raw SQL query and return results as list of dicts."""
    _ensure_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        conn.close()


def get_schema() -> str:
    """Return the database schema as a string for the query engine."""
    return """
    Table: shipments
    Columns:
      - id: INTEGER PRIMARY KEY (auto-increment)
      - file_name: TEXT (original file name)
      - document_type: TEXT (e.g., 'Bill of Lading', 'Commercial Invoice')
      - document_reference: TEXT (e.g., B/L number, invoice number)
      - consignee_name: TEXT
      - hs_code: TEXT
      - port_of_loading: TEXT
      - port_of_discharge: TEXT
      - incoterms: TEXT
      - description_of_goods: TEXT
      - gross_weight: TEXT
      - invoice_number: TEXT
      - customer_name: TEXT
      - overall_status: TEXT ('approved', 'needs_review', 'amendment_required')
      - decision: TEXT ('auto_approve', 'flag_for_review', 'amendment_required')
      - decision_reasoning: TEXT
      - draft_email: TEXT (amendment email draft, null if approved)
      - review_note: TEXT (review note for human, null if approved)
      - total_fields: INTEGER
      - matches: INTEGER
      - mismatches: INTEGER
      - uncertain: INTEGER
      - created_at: TEXT (ISO timestamp)
      - updated_at: TEXT (ISO timestamp)
    """
