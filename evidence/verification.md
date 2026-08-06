# Verification — Track B (AI Workflow and Validation)

Per the pack: *"Verification — tests, sample inputs/outputs, screenshots, metrics, or a repeatable manual test."* This file covers all five for each of the three components. Model used throughout: `llama-3.3-70b-versatile` via Groq.

---

## 1. Product Extraction (`pdf_extractor.py`)

**Sample inputs:** `messy_product_catalog_1.pdf`, `_2.pdf`, `_3.pdf` — 7 products across 5 currency formats (USD, INR, EUR, Rs., GBP), one product with no price, one with ambiguous stock status. See `evidence/sample_inputs/`.

**Sample output:** `evidence/sample_outputs/extracted_products.json` — the raw JSON returned by the app on the above inputs.

**Screenshot:** app's "Data Extraction Summary" panel, showing Total Items Extracted, Passed Pydantic Validation, and Data Integrity Rating.

**Metrics:**

| Metric | Value |
|---|---|
| Products extracted | 7 |
| Content-correct against manual ground truth | 7 / 7 |
| Passed strict Pydantic validation (per app) | 6 / 7 |
| Data Integrity Rating (per app) | 85.7% |

**Test detail (ground truth vs actual):**

| Product | Expected | Got | Result |
|---|---|---|---|
| Turbo Drill Pro | price 129.99, SKU AX-100 | price 129.99, SKU AX-100 | ✅ |
| Safety Goggles | price 799 (INR), SKU null | price 799.0, SKU null | ✅ |
| MEGA WRENCH | price 14.50 (EUR), out of stock | price 14.5, in_stock false | ✅ |
| Promo Hammer | price null (explicitly "unavailable") | price null | ✅ content-correct, ❌ fails Pydantic (see below) |
| Cable Tie Pack x100 | price 149, SKU CT100 | price 149.0, SKU CT100 | ✅ |
| Smart Sensor Node | price 56.75 (GBP), SKU SSN-88 | price 56.75, SKU SSN-88 | ✅ |
| Unknown Adapter | price 12.5, stock ambiguous ("?") | price 12.5, in_stock null | ✅ |

**Failure found and documented:** the app reports 6/7 passing strict validation, not 7/7. Promo Hammer is the failure — its `price` is correctly `null` (source text says "price unavailable"), but the schema in `pdf_extractor.py` defines `price` as a required float, so a correct `null` still fails validation. The extraction behavior is right; the schema doesn't yet allow "legitimately missing" as a valid state for price. Fix not yet applied: make `price` `Optional[float] = None`, matching how `sku` is already handled — left as a documented limitation rather than a same-day patch, since it needs a regression check against the other 6 items first.

**Repeatable manual test:** re-run the extractor on the same 3 PDFs and compare against the ground-truth table above.

---

## 2. Founder Brief Generation (`brief_generator.py`)

**Sample inputs:** `doc1_market.txt` through `doc5_strategy.txt` — 5 short source docs. See `evidence/sample_inputs/`.

**Sample output:** the generated Founder Brief (Executive Summary, Key Takeaways, Market & Operational Risks, Strategic Next Steps), captured in the app screenshot.

**Metrics:**

| Metric | Value |
|---|---|
| Bullets requiring citation | 13 (5 takeaways + 4 risks + 4 next steps) |
| Bullets with a citation tag | 13 / 13 |
| Citations manually traced to correct source doc | 13 / 13 |
| Fabricated facts found | 0 |

**Repeatable manual test:** for each cited bullet, open the source doc named in its `[DOCx_CHUNKy]` tag and confirm the claim is actually present there. With only 5 short docs this is a quick manual trace — e.g. the thermal-shielding risk cites `[DOC2_CHUNK_01]` and is confirmed present in `doc2_operations.txt`; the 72% budget figure cites `[DOC3_CHUNK_01]` and is confirmed present in `doc3_finance.txt`.

---

## 3. Candidate Email Drafting (`email_drafter.py`)

**Sample input:** `candidate_sample.json` — candidate Alexander Chen, status "Next Round", interview date 2026-08-10, notes on transformers knowledge and a remote-work request. See `evidence/sample_inputs/`.

**Sample output:** the generated subject line and email body, captured in the app screenshot, plus the app's own Fact-Gate analysis panel.

**Screenshot:** shows "Fact-Gate Status: WARNING" with one flagged infringement.

**Metrics:**

| Metric | Value |
|---|---|
| Real facts correctly used (name, position, date, notes) | 4 / 4 |
| Invented facts found | 0 |
| Fact-Gate false positives | 1 |

**Failure found and documented:** the Fact-Gate flagged the word "Additionally" as an unverified proper noun, purely because it's capitalized as a sentence-starter and isn't in the `COMMON_IGNORES` whitelist. This is a real, reproducible instance of the gap already noted in `ai_use_log.md` and the README's Known Limitations — the whitelist only covers words I'd already seen trip the check, not the general case of sentence-initial capitalization. Not yet fixed: would need a general exception for sentence-initial words rather than an ever-growing word list; left undone pending its own test pass.

**Repeatable manual test:** re-run the drafter on `candidate_sample.json`, compare the output against the source JSON field by field, and check the Fact-Gate panel for any flags that don't correspond to an actual invented fact.

---

## Summary

| Component | Test size | Result |
|---|---|---|
| Product extraction | 7 products, 3 PDFs | 7/7 content-correct; 6/7 passed strict validation — 1 schema gap found, documented |
| Founder Brief | 5 source docs, 13 cited bullets | 13/13 citations verified correct, 0 fabrication |
| Email drafter | 1 candidate | 4/4 facts correct, 0 invented; 1 fact-gate false positive, documented |
