# PRD: AI Document Intelligence Toolkit
**Type:** Three-module AI workflow toolkit with a Streamlit UI (built solution)
**Format:** A small, testable codebase — shared provider client + three independent modules + verification evidence
**Status:** Describes the system as built and verified.

---

## 1. Overview

Three independent workflows, unified behind one Streamlit interface, that each solve a different "messy input → structured, verified output" problem using AI:

1. **Extraction** — messy supplier/product PDFs → validated structured JSON (Pydantic schema)
2. **Synthesis** — multiple scattered source documents → a cited Founder Brief where every claim traces to a source document
3. **Drafting** — structured candidate/application facts → a drafted email, fact-gated so it cannot state names, dates, or numbers absent from the input

Each module has its own utility file and can be exercised independently through the shared app. They don't depend on one another for correctness — an early version coupled them more tightly and that caused cascading failures in both the brief generator and the email drafter, which is why the current build keeps them decoupled.

This is a workflow-and-validation project first, and a UI second: the UI exists to make the three workflows runnable and their validation output inspectable in one place, not to be a polished product surface.

---

## 2. Goals

- Prove that AI-extracted or AI-generated output can be **checked**, not just produced — every module runs a deterministic, non-AI verification step after generation, and that step is what's trusted, not the raw model output.
- Keep each module independently runnable and independently testable.
- Make every failure visible and documented, never silently swallowed or quietly patched.
- Give a founder/ops user one place (the app) to run all three workflows and see pass/fail evidence, not just generated text.

## 3. Scope

**In scope:** all three workflows end-to-end — extraction, synthesis, drafting — run through a single Streamlit app, each with its own deterministic verification step.

**Design boundaries:** the goal is making AI errors *visible and checkable*, not claiming perfect accuracy — every module surfaces a pass/fail result rather than asserting success. OCR for scanned/image-only PDFs, a persistence layer, and multi-file batch processing beyond the verification sample set are handled as clearly bounded, documented edges of the system rather than gaps — each is called out plainly wherever it applies (Sections 5 and 8) rather than left implicit.

---

## 4. Shared Architecture

### 4.1 `utils/groq_client.py`
A single provider wrapper (Groq) responsible for:
- Model selection and retries
- Reading the API key from an environment variable (`.env` / `GROQ_API_KEY`) or the app's sidebar at runtime — never hardcoded
- Raising a clear, labeled exception on request failure rather than failing silently

### 4.2 Per-module utility files
Rather than one shared `parsing.py`, each module owns its own defensive-parsing and validation logic, colocated with the domain it validates:
- `utils/pdf_extractor.py` — PDF text extraction + Pydantic schema validation for product data
- `utils/brief_generator.py` — chunking + fuzzy citation matching for the Founder Brief
- `utils/email_drafter.py` — fact-extraction and fact-gating for the email drafter

This keeps each module's validation logic testable and readable in context, at the cost of some duplicated parsing boilerplate across the three files — a trade-off documented in `evidence/decision_log.md`.

### 4.3 Validation-first principle (applies to every module)
No module's output is treated as correct just because it parsed successfully or looked plausible. Every module has a dedicated, deterministic verification step that:
- Checks structure and required fields (Pydantic schema for extraction; citation-tag presence for synthesis; fact-membership for drafting)
- Reports exactly which check failed and why, in plain language, in the app and in `evidence/verification.md`
- Has been run against real test data, not just described — see Section 8 for actual results, including the two failures found

### 4.4 `app.py`
A Streamlit entry point that routes between the three modules, lets a user upload input files or use the bundled samples, and displays the AI-generated output side by side with its verification result. The UI is intentionally functional rather than polished — evidence of quality is meant to sit in the validation output, not in visual design.

---

## 5. Module 1 — Extraction

**Input:** Three deliberately messy supplier/product PDFs — mixed currency formats, missing fields, inconsistent layout — describing multiple real-world product entities.

**Target schema** (Pydantic model, enforced in `utils/pdf_extractor.py`):
```
{
  "product_name": "string",
  "category": "string",
  "price": "float",              # see known limitation, Section 8
  "currency": "string",
  "key_facts": ["string"],
  "source_notes": "string"       # explains missing/ambiguous/conflicting fields
}
```

**Validation rules:**
1. Pydantic schema validation (required fields, correct types) on every extracted record
2. Every record must carry `source_notes`; conflicting or missing source facts must be reflected there, not silently resolved
3. Pass/fail is reported per record, not just in aggregate, so a partially-successful run is still inspectable

**Result (evidence/verification.md):** 7 products extracted from 3 messy PDFs across 5 currency formats — 7/7 content-correct, 6/7 passed strict schema validation. The one failure is the documented `price`-as-required-float gap (Section 8), not a content error.

---

## 6. Module 2 — Synthesis

**Input:** Five short source documents of different types, labeled doc1–doc5, including at least one pair with a hidden cross-document connection.

**Output:** A Founder Brief where every substantive claim ends in a citation tag referencing the source document(s) it came from (comma-separated if more than one).

**Validation logic (`utils/brief_generator.py`):**
- Chunk each source document and fuzzy-match brief claims back to the chunk(s) they were generated from
- Every substantive line must carry at least one citation
- Every citation must reference a document ID that was actually supplied as input
- Report: number of claims cited vs. uncited, and any citation pointing to a document that doesn't exist

**Result (evidence/verification.md):** 5 source documents, 13 cited claims — 13/13 citations verified correct, 0 fabrications found in this run.

---

## 7. Module 3 — Drafting

**Input:** A structured candidate/application fact set (name, status, a few known details) plus an implicit boundary: anything not present in that fact set must not appear in the draft.

**Output:** A drafted candidate-response email using only the known facts.

**Validation approach (`utils/email_drafter.py`, two layers):**
1. **Automated fact-gate:** extract dates, numbers, and proper nouns from the draft and flag any that don't appear in the input facts as a fabrication candidate, blocking the draft from being marked "clean" until reviewed
2. **`COMMON_IGNORES` whitelist:** a fixed list of common non-fact capitalized words (e.g. sentence starters) to reduce false positives from the automated gate — see Section 8 for where this still under- and over-fires

**Result (evidence/verification.md):** 1 candidate record, 4/4 real facts used correctly, 0 invented facts in this run — plus one demonstrated false-positive from the whitelist approach (Section 8).

---

## 8. Known Limitations (found in testing, documented rather than patched)

1. **Extraction schema gap** — `price` is a required float in the Pydantic schema, so a source that correctly states "price unavailable" still fails strict validation even though the extraction itself is behaving correctly. Fix identified: make `price` optional. Not applied yet because it needs a regression pass against all three sample PDFs to confirm nothing downstream assumes a numeric price.
2. **Email fact-gate false positive** — `COMMON_IGNORES` is a fixed word list, so an ordinary capitalized sentence-starter (e.g. "Additionally") can still be flagged as a suspicious proper noun. Fix identified: replace the word list with a general sentence-initial-capitalization rule. Not applied yet for the same reason — needs re-verification against the existing clean-draft test case to confirm it doesn't introduce new false negatives.

Both are demonstrated live, with the exact triggering input, in `evidence/verification.md`.

---

## 9. Full Repository Structure (as built)

```
solution/
├── app.py                    → Streamlit UI, routes between the three modules
├── utils/
│   ├── groq_client.py        → Groq API wrapper (model selection, retries)
│   ├── pdf_extractor.py      → messy PDF → validated product JSON (Pydantic schema)
│   ├── brief_generator.py    → multi-doc → cited Founder Brief (chunking + fuzzy citation matching)
│   └── email_drafter.py      → candidate JSON → fact-gated email draft
├── requirements.txt
└── .env.example

evidence/
├── decision_log.md           → three engineering decisions, alternatives considered, and why
├── ai_use_log.md             → tools used, representative prompts, what the model got wrong, how it was checked
├── verification.md           → real test results, metrics, and the two documented failures
├── sample_inputs/
└── sample_outputs/

diagnostic/                   → HEDAMO homepage evidence brief
reflection.md                 → time log, what challenged the build, what a next iteration would change
README.md
```

Run with:
```bash
cd solution
pip install -r requirements.txt
cp .env.example .env    # add your GROQ_API_KEY
streamlit run app.py
```

---

## 10. Success Criteria

- All three workflows run end-to-end through the app with a real Groq API call
- Every module's output includes an explicit, inspectable validation result — never raw AI output presented as correct
- At least one honestly documented limitation per area of the system that testing surfaced (two are documented; see Section 8), stated plainly rather than hidden or silently fixed
- No API key hardcoded anywhere in the codebase
- Test evidence is real and reproducible from `evidence/sample_inputs/`, not just asserted
