# AI Document Intelligence Toolkit — AFAP Submission

**Track B: AI workflow and validation** | Altibbe Founder Assessment Programme

---

## The problem and the user

A founder's office deals with messy, unstructured inputs constantly — supplier catalogs with inconsistent formatting, scattered documents that need synthesizing into a decision-ready brief, and candidate data that has to become a professional, fact-accurate email without a human re-typing it every time.

The user is a founder or ops lead who needs three things done fast, correctly, and *verifiably* — not just "AI did it and it looked fine."

This toolkit does three things:

1. **Extracts structured product data** from messy, inconsistently-formatted PDFs (mixed currencies, missing fields, ambiguous values) into validated JSON.
2. **Synthesizes a cited Founder Brief** from multiple source documents, where every claim traces back to the exact source it came from.
3. **Drafts candidate emails** from structured application data — with a deterministic fact-check that blocks the email from inventing names, dates, or numbers not present in the source.

## Why this approach

Every component follows the same pattern: **let the LLM do the generation, then verify it deterministically before trusting the output.** None of the three modules trust the model's output at face value — each has a local, non-AI check sitting after the AI step. That pattern, and why it was chosen over the alternatives, is documented in [`evidence/decision_log.md`](evidence/decision_log.md).

## Scope

**In scope:** the three Track B tasks above, end-to-end, with a Streamlit UI to run and inspect all three.
**Out of scope (by design, given the time cap):** UI polish beyond functional, multi-file batch processing beyond the sample set, and automatic remediation of the two known gaps below (documented, not silently patched).

## Results — this isn't a claim, it's tested

| Component | Test | Result |
|---|---|---|
| Product extraction | 7 products, 3 messy PDFs, 5 currency formats | 7/7 content-correct; 6/7 passed strict schema validation |
| Founder Brief | 5 source docs, 13 cited claims | 13/13 citations verified correct, 0 fabrication |
| Email drafter | 1 candidate record | 4/4 real facts used correctly, 0 invented facts |

Full test detail, sample inputs/outputs, and the two real failures found (and left honestly documented rather than quietly fixed) are in [`evidence/verification.md`](evidence/verification.md).

## Setup and run

```bash
# from /solution
pip install -r requirements.txt
cp .env.example .env    # add your GROQ_API_KEY
streamlit run app.py
```

The app runs locally at `localhost:8501`. Add your `GROQ_API_KEY` either in `.env` or directly in the app's sidebar once it's running — both work. Upload the sample files from `evidence/sample_inputs/` to reproduce the results in `evidence/verification.md`.

## Architecture

```
app.py                  → Streamlit UI, routes between the three modules
utils/groq_client.py    → Groq API wrapper (model selection, retries)
utils/pdf_extractor.py  → messy PDF → validated product JSON (Pydantic schema)
utils/brief_generator.py→ multi-doc → cited Founder Brief (chunking + fuzzy citation matching)
utils/email_drafter.py  → candidate JSON → fact-gated email draft
```

Each module is independent — extraction doesn't depend on brief generation or vice versa — deliberately, after an early version had them too loosely interlinked and both the brief generator and email drafter failed as a result (see [`reflection.md`](reflection.md)).

## Known limitations

Two real gaps were found during testing and are left as documented limitations rather than quick patches, since fixing either needs its own regression pass:

1. **Extraction schema gap** — `price` is a required float in the Pydantic schema, so a *correctly* missing price (source says "unavailable") still fails strict validation even though the extraction behavior itself is right. Fix: make `price` optional.
2. **Email fact-gate false positive** — the fact-check whitelist (`COMMON_IGNORES`) is a fixed word list, so it can still flag an ordinary capitalized sentence-starter (e.g. "Additionally") as a suspicious proper noun. Fix: replace the word list with a general sentence-initial-capitalization rule.

Both are demonstrated live in [`evidence/verification.md`](evidence/verification.md) with the exact input that triggers each.

## Evidence pack

- [`diagnostic/`](diagnostic/) — HEDAMO homepage evidence brief
- [`evidence/decision_log.md`](evidence/decision_log.md) — three engineering decisions, alternatives, and why
- [`evidence/ai_use_log.md`](evidence/ai_use_log.md) — tools, prompts, what the model got wrong, how it was checked
- [`evidence/verification.md`](evidence/verification.md) — real test results, metrics, and two documented failures
- [`evidence/sample_inputs/`](evidence/sample_inputs/) and [`evidence/sample_outputs/`](evidence/sample_outputs/) — the actual test data and actual outputs
- [`reflection.md`](reflection.md) — time log, what challenged me, what I'd do with one more day
