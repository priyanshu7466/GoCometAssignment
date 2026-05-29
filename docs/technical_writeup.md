# Technical Write-up — Nova Trade Document Pipeline

## 1. Architecture

```
         ┌─────────────────────────────────────────────────────┐
         │                  Client (Browser)                    │
         │          Upload PDF → View Results → Query           │
         └──────────────────────┬───────────────────────────────┘
                                │ HTTP
                                ▼
         ┌─────────────────────────────────────────────────────┐
         │              FastAPI Server (:8000)                  │
         │                                                     │
         │  POST /api/process ─────────────────────────────┐   │
         │                                                 │   │
         │  ┌──────────────┐                               │   │
         │  │   1. SAVE    │  Write file to data/uploads/  │   │
         │  └──────┬───────┘                               │   │
         │         ▼                                       │   │
         │  ┌──────────────┐  Gemini 2.0 Flash (Vision)    │   │
         │  │ 2. EXTRACTOR │  PDF → JSON + confidence      │   │
         │  └──────┬───────┘                               │   │
         │         ▼  structured JSON                      │   │
         │  ┌──────────────┐  Deterministic rules engine    │   │
         │  │ 3. VALIDATOR │  JSON + rules → verdicts      │   │
         │  └──────┬───────┘                               │   │
         │         ▼  validation result                    │   │
         │  ┌──────────────┐  Gemini 2.0 Flash (Text)      │   │
         │  │  4. ROUTER   │  Decide + reason + draft      │   │
         │  └──────┬───────┘                               │   │
         │         ▼  routing decision                     │   │
         │  ┌──────────────┐                               │   │
         │  │  5. STORE    │  SQLite → data/shipments.db   │   │
         │  └──────────────┘                               │   │
         │                                                     │
         │  POST /api/query ───────────────────────────────┐   │
         │  │ NL question → Gemini → SQL → Execute → Answer│   │
         │  └──────────────────────────────────────────────┘   │
         └─────────────────────────────────────────────────────┘

Data flow: Each agent's output is the next agent's input.
State: Each stage persists to SQLite before proceeding.
Communication: Structured JSON handoff — no shared mutable state.
```

## 2. Three Nastiest Failure Modes (from real testing)

### Failure 1: LLM returns non-JSON response

**What happened:** On a particularly complex multi-page PDF, Gemini sometimes wrapped its response in markdown code fences (` ```json ... ``` `) or added explanatory text before the JSON.

**How I handled it:** 
- Strip markdown code fences from the response before parsing
- If JSON parsing still fails, the extractor returns a structured error with `_error` and `_raw_response` fields
- The API returns a 422 with a clear error message instead of crashing silently

**What I'd do with more time:** Add a retry with a more explicit "return ONLY valid JSON" prompt, and implement JSON repair parsing (e.g., find the first `{` and last `}` and try to parse that substring).

### Failure 2: Confidence score gaming

**What happened:** The LLM sometimes assigns 0.95 confidence to a field it clearly inferred rather than read from the document. Example: a Bill of Lading had no invoice number field, but the model returned `{"value": "N/A", "confidence": 0.85}` instead of `{"value": null, "confidence": 0.0}`.

**How I handled it:**
- Prompt engineering: explicit instruction "If a field is NOT found, return null with confidence 0.0. Never infer."
- The Validator treats any null value as a mismatch for required fields, regardless of confidence
- For production: I'd add a second-pass verification where another LLM call checks "is this field actually visible in the document?"

### Failure 3: Fuzzy matching false positives

**What happened:** The validator's fuzzy matching (SequenceMatcher) matched "Nordic Imports A/S" with "Nordic Imports ApS" at ~92% similarity — treating it as a match when it's actually a different legal entity type (A/S = Aktieselskab, ApS = Anpartsselskab in Danish law).

**How I handled it:**
- For entity names, the rule is set to "exact" match instead of "fuzzy"
- Added a similarity threshold sweet spot: >85% similarity → "uncertain" (not match), requiring human review
- For production: I'd add entity-type-aware matching that treats legal suffixes (Ltd, LLC, GmbH, A/S, ApS) as semantically significant

## 3. Observability — Tracing a Shipment in Production

If this ran for 50 customers, here's what I'd instrument:

**Per-shipment trace:**
- Unique `shipment_id` assigned at upload time
- Each agent logs: `{shipment_id, agent_name, start_time, end_time, input_hash, output_hash, status}`
- Stored in a structured log (Langfuse or OpenTelemetry traces)
- Any LLM call logs: model, prompt tokens, completion tokens, latency, cost

**Dashboard (what I'd show):**

| Panel | Metric | Why |
|-------|--------|-----|
| Throughput | Docs processed / hour | Capacity planning |
| Pipeline health | Success rate (%) | Are we breaking? |
| Latency | P50/P95 per agent | Where's the bottleneck? |
| Decision distribution | % approve / review / amend | Is the model drifting? |
| Cost | $/document, $/day | Budget tracking |
| Confidence distribution | Histogram of extraction confidence | Model quality over time |
| Override rate | % of agent decisions overridden by CG | Trust calibration |

**Alert triggers:**
- Pipeline error rate > 5% in 1 hour
- Average extraction confidence drops below 0.7
- Cost per document exceeds $0.01
- CG override rate exceeds 30% (agent is unreliable)

## 4. Cost — Back-of-Envelope

| Component | Input | Cost |
|-----------|-------|------|
| Extractor (Gemini Flash Vision) | ~1500 tokens (1-2 page PDF) | ~$0.00015 |
| Validator | No LLM call — pure Python | $0.00 |
| Router (Gemini Flash Text) | ~2000 tokens (validation JSON) | ~$0.00020 |
| Query (Gemini Flash Text) | ~500 tokens per question | ~$0.00005 |
| **Total per document** | | **~$0.0004** |

**At scale:**
- 1,000 docs/day = ~$0.40/day = ~$12/month
- 10,000 docs/day = ~$4.00/day = ~$120/month

**Where it blows up:**
- Multi-page documents (10+ pages) → extraction tokens scale linearly → use page selection/chunking
- Retry storms → if error rate spikes and every doc retries 3x → 3x cost → circuit breaker needed
- Query abuse → if users run 100 NL queries/day → queries are cheap but add up → cache frequent queries

## 5. Latency — Where's the Slowest Hop?

| Stage | Typical Latency | Bottleneck? |
|-------|----------------|-------------|
| File upload + save | ~50ms | No |
| **Extractor (Gemini Vision)** | **3–5 seconds** | **Yes — dominant** |
| Validator (Python rules) | ~5ms | No |
| Router (Gemini Text) | 1–2 seconds | Minor |
| Store (SQLite insert) | ~5ms | No |
| **Total pipeline** | **4–7 seconds** | |

**How to fix it:**
1. **Extractor is the bottleneck.** For production: pre-process PDFs to images on upload (async), cache extraction results by content hash, parallelize multi-page extraction.
2. **Batch processing:** When multiple docs arrive in one email, extract all in parallel rather than sequential.
3. **Model downgrade for simple docs:** If the doc is clearly formatted (e.g., digital PDF, not a scan), use a cheaper/faster model or even regex extraction as a first pass.

## 6. What I'd Do Differently with a Week

1. **Cross-document validation** — When a shipment has BOL + Invoice + Packing List, validate that consignee, HS code, and weight match across all three. Currently each doc is validated independently.

2. **Proper eval suite** — Build a test set of 20+ annotated trade docs with ground-truth field values. Run automated accuracy tests on every code change. Track extraction accuracy, validation precision/recall, and routing correctness over time.

3. **PDF preprocessing pipeline** — OCR fallback for scanned docs (via Tesseract), page detection to handle multi-page documents, image enhancement for low-quality scans before sending to the vision model.

4. **Structured output enforcement** — Use Gemini's JSON mode / response schema to guarantee valid JSON instead of prompt-based JSON extraction + post-processing cleanup.

5. **Proper observability** — Integrate Langfuse for LLM tracing, add OpenTelemetry spans for each pipeline stage, build a real monitoring dashboard.

6. **Customer rule management UI** — A simple CRUD interface for CG leads to create and edit customer rule sets without touching JSON files.
