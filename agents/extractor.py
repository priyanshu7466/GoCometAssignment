"""
Extractor Agent — Takes a trade document (PDF) and extracts structured fields
using OpenRouter's free Gemini 2.0 Flash endpoint.
"""

import json
import base64
import os
import fitz  # PyMuPDF
from openai import OpenAI

# Fields we extract from every trade document
REQUIRED_FIELDS = [
    "document_type",
    "document_reference",
    "consignee_name",
    "hs_code",
    "port_of_loading",
    "port_of_discharge",
    "incoterms",
    "description_of_goods",
    "gross_weight",
    "invoice_number"
]

EXTRACTION_PROMPT = """
You are an expert trade document AI. Your task is to extract the following specific fields from the provided trade document (Bill of Lading, Commercial Invoice, etc).

Extract exactly these fields:
{fields}

For each field, provide:
1. "value": The exact string found in the document. If the field is not present, return null.
2. "confidence": A float between 0.0 and 1.0 indicating how confident you are that this is the correct value. If value is null, confidence must be 0.0.

CRITICAL RULES:
- Return ONLY valid JSON.
- Never invent or infer missing values. Only extract what is visibly present.
- Do not add markdown formatting or explanation outside the JSON.

Example output format:
{{
  "document_type": {{"value": "Bill of Lading", "confidence": 0.95}},
  "consignee_name": {{"value": "Acme Corp", "confidence": 0.98}},
  "hs_code": {{"value": null, "confidence": 0.0}}
}}
"""

def pdf_to_base64_image(pdf_path: str) -> str:
    """Convert the first page of a PDF to a base64 encoded JPEG image."""
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    img_bytes = pix.tobytes("jpeg")
    return base64.b64encode(img_bytes).decode("utf-8")

def extract_fields(file_path: str) -> dict:
    """
    Extract structured fields from a trade document using OpenRouter.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return {"_error": "GROQ_API_KEY environment variable not set."}

    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
    )
    
    try:
        base64_image = pdf_to_base64_image(file_path)
        prompt = EXTRACTION_PROMPT.format(fields=", ".join(REQUIRED_FIELDS))

        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        return json.loads(content.strip())
        
    except json.JSONDecodeError as e:
        return {"_error": f"JSON parsing failed: {str(e)}", "_raw_response": content}
    except Exception as e:
        return {"_error": str(e)}
