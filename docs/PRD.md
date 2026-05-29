# PRD: Trade Document Validation — Multi-Agent Pipeline (Part 1)

**Author:** Priyanshu Ranjan · **Date:** 2025-05-29 · **Scope:** Part 1 of GoComet Nova FDE Assignment

---

## 1 | Nova Understanding

### What is Nova?

Nova is GoComet's bet that logistics can't be solved with another dashboard. It's a governed multi-agent AI platform built on four pillars: a **Workflow Orchestrator** (YAML-defined workflows rendered as React Flow graphs), an **Agents Orchestrator** (LangGraph-powered, 5-stage agent pipelines), a **No-Code App Builder** (so ops teams can ship internal tools without filing Jira tickets), and a **Data Layer** (ClickHouse for analytics, Weaviate for semantic search).

Why does this exist? Because logistics is fundamentally exception-driven. A freight forwarder in Rotterdam has different document rules than one in Singapore. A consumer goods importer has different HS code validation logic than a chemical importer. You can't hardcode this into features — you'd end up with a settings page that has 400 toggles. Nova instead makes workflows *configurable* and lets AI agents handle the repetitive 80% (read this PDF, check these fields, draft this email) while humans focus on the 20% that actually requires judgment. The governance layer (OpenFGA for auth, Langfuse for observability, LiteLLM for model routing) exists because enterprise clients won't hand over document processing to a black box — they need audit trails, role-based access, and cost controls.

### What is the FDE model?

The Forward Deployed Engineer model flips the traditional engineering org chart. Instead of building features against a product backlog and hoping customers use them, FDEs operate as a **2-in-a-box pair** — one engineer, one client partner — and own outcomes end-to-end. You're not shipping a ticket; you're making sure the client's document validation workflow actually works in production.

GoComet uses this model for Nova because there's no such thing as a "generic" logistics client. Company A validates HS codes against a 6-digit lookup table. Company B requires 8-digit codes and cross-references them against a restricted goods list. Company C doesn't care about HS codes at all but will reject any shipment where the consignee name has a single typo. A product team sitting in an office can't anticipate all of this. An FDE sitting *with* the client can discover the rule in a 10-minute conversation, encode it that afternoon, and deploy it the next morning. The FDE model turns the gap between "what the product does" and "what the client needs" from a 6-month feature request into a same-week configuration.

### What does "System of Outcomes" mean?

Most enterprise software falls into two buckets. **Systems of Record** (your ERP, your TMS) store data — they know a shipment exists. **Systems of Engagement** (dashboards, notifications, Slack bots) help people interact with that data — they tell you a shipment is delayed. Neither of them *does* anything about it.

A **System of Outcomes** produces results. It doesn't just record that a Bill of Lading has a mismatched port code — it extracts the field, compares it against the customer's rules, drafts the amendment email, and hands the CG operator a ready-to-send message. The operator's job shifts from "read every field and check it" to "review the agent's work and hit send." Nova is a System of Outcomes because its agents deliver measurable output: validated documents, drafted amendments, approval decisions — not just charts showing how many documents are pending.

---

## 2 | Problem Statement

### Where the current flow breaks

Today, trade document validation works like this: a supplier (SU) emails PDFs — Bill of Lading, Commercial Invoice, Packing List, Certificate of Origin — to a control group (CG) operator. The operator opens each PDF, reads every field, and checks it against customer-specific rules. If something's wrong, they type an amendment request and email it back. Then they wait. 2–4 amendment cycles per shipment is normal.

| Failure Mode | Impact |
|---|---|
| **Rules live in people's heads** | New hires make avoidable mistakes for weeks. When an experienced CG operator leaves, their institutional knowledge walks out with them. |
| **Manual field-by-field reading** | Slow (4–24 hrs per amendment cycle) and error-prone. A tired operator at 4 PM misses a wrong HS code that a fresh operator at 9 AM would catch. |
| **No audit trail** | When a dispute arises, there's no evidence of what was checked, when, and by whom. Just email threads. |
| **No visibility** | A CG lead can't answer "how many shipments are pending review right now?" without manually counting emails. |
| **CG bandwidth is the bottleneck** | Throughput is limited by how fast humans can read. You can't scale by adding more shipments — you scale by adding more people. |
| **Each cycle adds 4–24 hrs of delay** | Multiply by 2–4 cycles per shipment and you're looking at days of delay that are purely operational, not logistical. |

### What success looks like — first 5 minutes for a CG operator

Upload a document. In under 10 seconds, see every extracted field with a confidence score. See which fields matched customer rules (green), which mismatched (red), and which are uncertain (amber). For every mismatch, see *what was found* vs. *what was expected*. If the decision is "amend," get a pre-drafted email listing every discrepancy — review it, edit if needed, send. Understand *why* the agent flagged something, not just *that* it did.

---

## 3 | Users + Jobs-to-be-Done

### Personas

| Persona | Role | Core concerns |
|---|---|---|
| **CG Operator** | Validates shipment docs against customer requirements | Speed, accuracy, not missing a mismatch, reducing amendment cycles |
| **SU (Supplier)** | Generates and sends shipment docs | First-submission approval, knowing what's wrong quickly, fast CG turnaround |

### JTBD Statements

1. **When** I receive a new shipment email with 3 attached docs, **I want to** see all extracted fields and validation results in one consolidated view, **so that** I can review a shipment in 30 seconds instead of 15 minutes.

2. **When** the agent flags a mismatched HS code, **I want to** see exactly what was found vs. what's expected and where in the document the value was extracted from, **so that** I can trust the flag and act on it immediately without re-reading the PDF.

3. **When** all fields match across all documents, **I want** the system to auto-approve and store the verified output, **so that** I only spend time on shipments that actually need my attention.

4. **When** I need to send an amendment back to the supplier, **I want** a pre-drafted email listing every discrepancy with found/expected values, **so that** I can review, edit if needed, and send in under a minute.

5. **When** my manager asks how many shipments are pending review this week, **I want to** pull that number from the system in seconds, **so that** I can answer without digging through email threads.

6. **(SU)** **When** I receive an amendment request, **I want** a clear, itemized list of exactly which fields need fixing and what the correct values should be, **so that** I can fix everything in one resubmission instead of going back and forth 3 times.

---

## 4 | Agent Architecture

### Why 3 agents, not 1 prompt?

Separation of concerns. Extraction (read pixels → structured data) is a fundamentally different task from validation (compare data against rules) which is different from routing (make a decision). A single mega-prompt would conflate all three, making debugging a nightmare and blowing up the hallucination surface area. With 3 agents, you can swap the extraction model without touching validation logic, change customer rules without retraining anything, and A/B test routing independently.

### Why not 5 agents?

More agents = more handoff points = more latency and more failure modes. Three maps exactly to three distinct responsibilities. A 4th agent for "formatting" or a 5th for "storage" would add orchestration overhead without functional value.

### Agent Specifications

| Agent | Input | Output | Responsibility |
|---|---|---|---|
| **Extractor** | PDF / image file | JSON: `{ fields: [{ name, value, confidence }] }` | Pure extraction. Read the document, pull out structured fields. No judgment, no comparison. |
| **Validator** | Extracted JSON + customer rules (JSON) | JSON: `{ results: [{ field, status: match\|mismatch\|uncertain, found, expected }] }` | Pure comparison. Check each extracted field against the rule set. No decisions. |
| **Router** | Validation result JSON | JSON: `{ decision: approve\|flag\|amend, reasoning, draft_email? }` | Pure decision-making. Look at the validation summary and decide what happens next. |

### How do agents communicate?

Structured JSON handoff. No shared mutable state. Each agent receives the previous agent's output as its input. It's a simple linear pipeline: **E → V → R**. If the topology were more complex (branching, parallel paths, human-in-the-loop loops), we'd use LangGraph. But a linear chain doesn't need a graph orchestrator — it needs clean function calls.

### How does state survive a crash?

Each agent's output is persisted to **SQLite** before the next agent runs. If the pipeline crashes at step 2, we resume from the stored extractor output. Every agent call is idempotent — re-running with the same input produces the same output.

---

## 5 | LLM & Tooling Choices

| Decision | Choice | Rationale |
|---|---|---|
| **Extraction model** | Gemini 2.0 Flash (vision) | Free tier available, strong vision capabilities, fast inference. Trade docs are structured enough that Flash handles them well. Fallback: if confidence is low, re-prompt with enhanced extraction instructions. |
| **Validation model** | Gemini 2.0 Flash | Rule comparison is simple enough for Flash. Structured JSON output mode enforces schema compliance. |
| **Routing model** | Gemini 2.0 Flash | Decision logic is straightforward. Flash is cost-effective for this. |
| **Why not GPT-4o?** | Cost | GPT-4o is ~3–5× more expensive with similar quality for structured doc extraction. Gemini Flash offers better cost-performance for this use case. |
| **Orchestration** | Custom Python (not LangGraph) | Pipeline is linear (E→V→R). LangGraph adds value for complex topologies — branches, loops, parallel execution. Here it adds a dependency without functional benefit. If Part 2 requires branching, we add it then. |
| **Structured output** | JSON schema enforcement | Used for extraction and validation outputs. *Not* used for the draft amendment email in routing — that needs free-form natural language. |

### Cost & Latency Estimates

| Metric | Estimate |
|---|---|
| Flash pricing | ~$0.10 / 1M input tokens |
| Tokens per trade doc | ~1,500 (2–3 page PDF as image) |
| **Cost per document (full pipeline)** | **~$0.001–0.003** |
| Extraction latency | ~3–5s (vision is the bottleneck) |
| Validation latency | <1s |
| Routing latency | <1s |
| **Total pipeline latency** | **~5–7s** |

---

## 6 | Trust, Failure Handling & Evals

### Anti-hallucination guardrails

- **Extractor prompt constraint:** *"Only extract fields that are visibly present in the document. If a field is not found, return null with confidence 0.0. Never infer or guess."*
- **Confidence scores** force the model to quantify uncertainty per field rather than producing false-confident output.

### Low-confidence handling

Any field with **confidence < 0.7** is marked `uncertain` by the validator. Uncertain fields **always** surface to the CG operator — never silently approved. The UI renders uncertain fields in amber.

### Loop & cost protection

- Max **1 retry** per agent. If retry also fails → mark as `failed — requires manual review` and surface it.
- No infinite retries. **Total pipeline timeout: 60 seconds.**
- If the extractor returns all-null fields, skip validation/routing and surface immediately as "extraction failed."

### Eval plan

| Eval Type | Method | What it measures |
|---|---|---|
| **Offline** | Test set of 10–20 trade docs with ground-truth field values | Extraction accuracy (field-level precision/recall), validation accuracy (correct match/mismatch), routing accuracy (correct approve/flag/amend) |
| **Online** | Track CG operator agreement rate | % of cases where the agent's recommendation matched the CG's final action. If this drops over time, the agent is drifting. |

---

## 7 | Metrics & Success Criteria

### North-star metric

**First-pass document approval rate** — % of shipments that pass validation with zero amendment cycles.
- **Today:** ~30–40%
- **Target:** 70%+ after agent-assisted validation

### Supporting metrics

| # | Metric | What it tells us |
|---|---|---|
| 1 | Extraction accuracy | % of fields correctly extracted vs. human ground truth |
| 2 | Validation precision | % of flagged mismatches that are true mismatches (not false alarms) |
| 3 | Time to first review | Seconds from doc upload to CG seeing validation results |
| 4 | Amendment cycle reduction | Avg cycles per shipment, before vs. after |
| 5 | Confidence calibration | When the agent says 0.9 confidence, is it right 90% of the time? |
| 6 | Pipeline reliability | % of docs processed without errors |
| 7 | Cost per document | API spend per document processed end-to-end |

### Go / No-Go for 2-week pilot

| | Criteria |
|---|---|
| ✅ **GO** | Extraction accuracy ≥ 85% on 8 key fields. Zero silent approvals on mismatched fields. CG operators report time savings in exit survey. |
| ❌ **NO-GO** | Extraction accuracy < 70%. Any case of silent approval on a true mismatch. Pipeline fails on > 10% of documents. |

---

## 8 | What's Next (after Part 1 ships)

| Timeframe | Deliverable | Why this order |
|---|---|---|
| **Week 1** | Wire pipeline to a real email trigger — watch an inbox, auto-process new attachments. Add cross-document validation (consignee, HS code must match across BOL + Invoice + Packing List). | Email trigger is the highest-value unlock: removes the manual upload step entirely. Cross-doc validation catches errors that per-doc validation misses. |
| **Week 2** | Build a CG dashboard: pending reviews, processed today, flagged shipments. Add feedback loop — when CG overrides the agent's decision, log it as training signal for future model tuning. | Dashboard gives CG leads visibility they've never had. Feedback loop ensures the system gets better over time instead of drifting. |

---

*This PRD covers Part 1 scope: a working 3-agent pipeline (Extract → Validate → Route) with a simple upload interface, demonstrating the core value loop. Everything in Section 8 is post-Part 1.*
