# PRD: Trade Document Validation Pipeline (Part 1)

**Author:** Priyanshu Ranjan
**Date:** May 29, 2025
**Scope:** Part 1 of the GoComet Nova FDE Assignment

---

## 1 | Nova & The FDE Model

### What is Nova?
Honestly, Nova is GoComet's answer to the fact that logistics can't be solved with just another SaaS dashboard. Every freight forwarder has different rules for their documents. If you try to hardcode all that logic into a standard product, you end up with a settings page that has 400 toggles and a massive tech debt problem. 

Instead, Nova is a governed multi-agent AI platform. It's built on a Workflow Orchestrator, an Agents Orchestrator (running LangGraph), a No-Code App Builder, and a Data Layer. Basically, it makes logistics workflows configurable. The AI agents handle the repetitive grunt work (reading PDFs, cross-checking fields, writing emails), while humans step in only when real judgment is needed. The "governed" part is crucial—enterprise clients won't trust a black box, so things like OpenFGA for auth and Langfuse for observability are baked in to guarantee audit trails and safety.

### What is the FDE model?
The Forward Deployed Engineer (FDE) model flips the usual engineering org chart upside down. Instead of sitting in a back office building features against a Jira backlog and hoping users like them, FDEs work as a "2-in-a-box" pair alongside a client partner. We own the outcome from start to finish. 

GoComet uses this for Nova because there is no "generic" logistics client. One company might want to validate 6-digit HS codes against a specific table, while another rejects shipments if the consignee name has a single typo. A centralized product team can't anticipate every weird edge case. But an FDE sitting directly with the client can hear about a new rule on a Tuesday morning, encode it into Nova by the afternoon, and deploy it that same day.

### What is a "System of Outcomes"?
Most enterprise software is either a **System of Record** (like an ERP that just stores data) or a **System of Engagement** (like a dashboard that notifies you when something is late). Neither actually *does* the work for you.

A **System of Outcomes** actually produces a result. It doesn't just tell an operator "Hey, this Bill of Lading is wrong." It reads the document, catches the wrong port code, checks it against the database, drafts the amendment email, and hands the operator a ready-to-send message. The operator's job shifts from manual data entry to just reviewing and hitting send. It delivers measurable work.

---

## 2 | Problem Statement

### Where the current flow breaks
Right now, the trade document validation flow is a massive bottleneck. A supplier (SU) emails a batch of PDFs to a Control Group (CG) operator. The operator has to open every single PDF, read it field-by-field, and check it against whatever customer rules they have memorized. If they spot an error, they manually type out an email and wait for the supplier to fix it. This usually takes 2 to 4 back-and-forth amendment cycles per shipment.

Here's why this is broken:
- **Rules live in people's heads:** When an experienced operator leaves, all their knowledge leaves with them. New hires make mistakes for weeks.
- **Manual reading is error-prone:** A tired operator at 4 PM is going to miss a wrong HS code that they would have easily caught at 9 AM.
- **Zero visibility:** A manager can't easily see how many shipments are stuck in review without manually counting email threads.
- **Speed limits:** You can't scale the operation by adding more shipments; you can only scale by hiring more people, because throughput is hard-capped by human reading speed.

### Success in the first 5 minutes
If an operator uses our system for the first time, success looks like this: They upload a document. In under 10 seconds, they see exactly what was extracted, complete with confidence scores. They see instantly what matched their rules (green), what didn't (red), and what the AI was unsure about (amber). For any mistakes, they get a pre-drafted email ready to fire back to the supplier. They understand exactly why the system flagged something and can trust it enough to act on it immediately.

---

## 3 | Users + Jobs-to-be-Done

**Personas:**
1. **CG Operator:** Validates shipment docs. They care about speed, accuracy, and catching every single mismatch to reduce amendment cycles.
2. **SU (Supplier):** Generates the docs. They just want their shipments approved on the first try and need to know exactly what's wrong if something gets rejected.

**Jobs-to-be-Done (JTBD):**
1. **When** I get a new shipment email with 3 attached docs, **I want to** see all the extracted fields and validation results in one clear view, **so that** I can review the shipment in 30 seconds instead of 15 minutes.
2. **When** the system flags a mismatched HS code, **I want to** see exactly what was found versus what was expected, **so that** I can trust the flag without having to re-read the PDF myself.
3. **When** all fields match perfectly, **I want** the system to just auto-approve it, **so that** I only spend time on shipments that actually have problems.
4. **When** I need to send an amendment request, **I want** a pre-drafted email listing the exact discrepancies, **so that** I can review it and hit send in under a minute.
5. **When** my manager asks how many shipments are pending review, **I want to** pull that data instantly, **so that** I don't have to manually dig through my inbox.
6. **(SU)** **When** I receive an amendment request, **I want** an itemized list of what needs fixing and what the correct values are, **so that** I can fix it all in one go instead of going back and forth three times.

---

## 4 | Agent Architecture

### Why 3 agents instead of 1 mega-prompt?
Separation of concerns. Pulling data out of an image (extraction) is totally different from comparing that data against business rules (validation), which is different again from deciding what to do about it (routing). 

If we shoved all of this into one massive LLM prompt, debugging would be a nightmare and the chance of hallucinations would skyrocket. By splitting it into 3 agents, I can swap out the vision model without breaking the validation logic, and I can tweak the routing rules without messing up the extraction. 

### Why not 5 agents?
More agents just mean more handoff points, which means more latency and more places for things to break. Three agents map perfectly to the three jobs we need done. Adding a fourth agent just to format data would just add overhead.

### Agent breakdown:
- **Agent 1 (Extractor):** Takes the PDF image and outputs a structured JSON of the fields and confidence scores. Pure extraction. No judgment.
- **Agent 2 (Validator):** Takes the extracted JSON and compares it against the customer rules database. It just checks for matches or mismatches. Pure comparison.
- **Agent 3 (Router):** Looks at the validation results and makes a decision (approve, flag, or amend). If an amendment is needed, it drafts the email. Pure decision-making.

### How do they communicate?
It's a simple, linear pipeline (Extractor → Validator → Router). They pass structured JSON to each other. Because it's strictly linear, we don't need a heavy orchestrator like LangGraph just yet—clean function calls are much faster and simpler here.

Every time an agent finishes its job, the state is saved to a SQLite database. That way, if the Router agent hits a rate limit and crashes, we don't lose the extraction work. We can just pick up where we left off.

---

## 5 | Tech Stack & LLM Choices

| Role | Tool Choice | Why we chose it |
|---|---|---|
| **Extractor** | Groq `llama-4-scout` (Vision) | Strong vision capabilities and lightning-fast inference. Trade docs are structured enough that Llama 4 Scout handles them perfectly, and the Groq free tier is great for development. |
| **Validator** | Deterministic Python | LLMs are notoriously bad at exact string matching. Since rule comparison needs to be 100% exact (like checking if an HS code matches perfectly), we use pure Python code. It costs nothing, has zero latency, and is perfectly reliable. |
| **Router** | Groq `llama-3.3-70b` | Decision logic and email drafting require strong reasoning. Llama 3.3 70B is incredibly smart, and running it on Groq's LPU makes it practically instant. |
| **Why not GPT-4o?** | Cost & Latency | GPT-4o is significantly more expensive and slower. Groq's inference engine gives us sub-second text generation, which makes the UI feel snappy for the operator. |
| **Orchestration** | Custom Python | The pipeline is a simple straight line. Using LangGraph here would just add unnecessary bloat. If we need complex branching loops in the future, we'll migrate to it then. |

**Cost Estimates:** 
Running these models on Groq's preview tier is highly cost-effective (currently free for dev). Even at scale, processing a standard 2-page PDF trade document costs less than a fraction of a cent (~$0.001 - $0.003) end-to-end, with the whole pipeline taking about 5-7 seconds.

---

## 6 | Trust, Failures & Evals

### Stopping Hallucinations
The biggest risk is the AI making up data that isn't on the page. To fix this, the Extractor prompt strictly enforces: *"If a field is not visibly present, return null with confidence 0.0. Never infer or guess."* We also force the model to output a confidence score for every single field so we know when it's unsure.

### Handling Low Confidence
Silent approvals are dangerous. If the vision model extracts a field but gives it a confidence score below 0.7, the Validator automatically marks that field as `uncertain`. Uncertain fields are mathematically prevented from being auto-approved and will always be flagged in amber for a human to review.

### Guardrails
To prevent runaway API costs or infinite loops, each agent gets exactly 1 retry if it fails (like if it hits a rate limit or returns bad JSON). If it fails twice, the system just marks the document as "Failed - Requires Manual Review". We cap the whole pipeline timeout at 60 seconds.

### How we evaluate this
- **Offline Eval:** I'd put together a test set of 20 historical trade docs where we already know the right answers. We'd run the pipeline against it to measure extraction accuracy (precision/recall) and make sure the routing decisions match what a human would do.
- **Online Metric:** Once it's live, we track the **Operator Agreement Rate**—basically, how often does the human operator actually agree with the agent's decision? If that drops, we know the model is drifting.

---

## 7 | Metrics & Success Criteria

**The North-Star Metric:**
**First-pass document approval rate.** (The percentage of shipments that pass validation with zero amendment cycles). Right now, it's probably around 30-40%. We want to push that to 70%+.

**Supporting Metrics:**
1. **Extraction Accuracy:** % of fields correctly extracted versus human ground truth.
2. **Validation Precision:** Are the mismatches we flag actually mismatches, or just false alarms?
3. **Time to First Review:** How many seconds from upload to the operator seeing the results.
4. **Amendment Cycle Reduction:** Average cycles per shipment, before vs. after implementing Nova.
5. **Confidence Calibration:** When the AI claims 90% confidence, is it actually right 90% of the time?
6. **Pipeline Reliability:** % of docs processed without system errors or timeouts.
7. **Cost per Document:** Total API spend per shipment.

**Go / No-Go for a 2-week pilot:**
- **GO:** Extraction accuracy hits 85%+ on key fields. Zero cases of the system silently approving a mismatched field. Operators report feeling faster in an exit survey.
- **NO-GO:** Extraction accuracy is under 70%. The system silently approves a true mismatch. The pipeline crashes on more than 10% of documents.

---

## 8 | What's Next? (After Part 1)

If I had two more weeks to keep building, here's exactly what I'd tackle next:

1. **Week 1 - Email Ingestion & Cross-Doc Validation:** Right now, you have to manually upload a PDF. I'd wire the pipeline directly to an email inbox so it auto-processes attachments the second they arrive. I'd also build cross-document validation (e.g., checking that the HS Code on the Bill of Lading matches the HS Code on the Commercial Invoice). This catches the subtle errors that single-doc validation misses.
2. **Week 2 - Feedback Loops & Dashboards:** I'd build a proper dashboard for CG managers to see pending reviews and flagged shipments. More importantly, I'd build a feedback loop: when a human operator overrides the AI's decision, we save that correction to a vector database (like Weaviate) to use as few-shot training data so the agent doesn't make the same mistake twice. 
