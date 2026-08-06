# AI-Use Log — Track B (AI Workflow and Validation)

## Tools used

- **Groq API** (`groq` Python SDK, `llama-3.3-70b-versatile` as the default model) — used across all three components: PDF product extraction, Founder Brief generation, and candidate email drafting. The app also lets you swap in `llama-3.1-8b-instant`, `mixtral-8x7b-32768`, or `gemma2-9b-it` from the UI.
- Used an AI coding assistant (Antigravity) to help write and debug the Python code itself — not just for the LLM calls inside the app.

---

## Two representative prompts

**1. Product extraction (`pdf_extractor.py`)** — system prompt sent with every PDF text chunk:

> You are an expert product data extraction assistant. Extract all identifiable products from raw catalog/invoice text into a strict JSON schema (product_name, sku, price as float with currency stripped, category, specifications, in_stock). Only output valid JSON, no markdown wrapping, no commentary.

**2. Founder Brief generation (`brief_generator.py`)** — system prompt enforcing citations:

> You are an elite business analyst. Write a Founder Brief with Executive Summary, Key Takeaways, Market & Operational Risks, and Strategic Next Steps sections. Every bullet in the last three sections must end with a citation to the source chunk, formatted like [DOC1_CHUNK_03]. Do not fabricate facts not present in the chunks. Do not invent citation IDs.

---

## What the model got wrong, and how I checked

**1. Price formatting.** The extraction prompt explicitly says "strip any currency symbols, e.g. '$129.99' -> 129.99," but the model still frequently returned prices as strings like `"$129.99"` or `"Rs. 250"` instead of plain floats. Feeding that straight into the Pydantic schema crashed validation. I caught this by running it against sample catalog text and watching the app throw a type error — not something I found by reading the prompt, only by actually running it. Fixed it by pre-cleaning price strings (stripping `$`, `€`, `£`, commas) before the schema check, rather than trying to fix it with more prompt wording.

**2. False "hallucination" flags in the email drafter.** My own fact-checking regex (`verify_email_facts`) is supposed to catch invented names, dates, and numbers by flagging any capitalized word that isn't in the source JSON. When I first ran it, it was flagging completely normal words — "Dear," "Monday," "Recruiting Manager," "Thanks" — as suspicious, just because they're capitalized and weren't literally present in the input data. This wasn't the LLM getting something wrong, it was my own verification code being too strict. I checked this by reading through a few generated emails and the corresponding flag output side by side, saw the false positives were all ordinary email vocabulary, and built a `COMMON_IGNORES` whitelist (day/month names, common salutations, recruiting-email boilerplate) to filter them out without loosening the check on things that actually matter — real names, real numbers, real dates.

**3. Citations that don't line up as exact text.** The brief generator asks the model to tag every claim with a chunk ID like `[DOC1_CHUNK_02]`, but the sentence attached to that tag is a paraphrase, not a direct quote from the source. A plain substring search for the cited sentence in the source chunk fails almost every time because the wording doesn't match exactly. I checked this by trying to highlight cited sentences in the source text and watching the direct match come back empty. Fixed it with a fuzzy matcher (`find_best_sentence_match`) that scores word overlap between the cited sentence and every sentence in the source chunk, and picks the best match instead of requiring an exact one.

---

## Pattern

All three checks came from actually running the tool against sample data and seeing what broke, not from anticipating problems in advance. In each case the fix was a small deterministic check placed after the LLM step, not a prompt tweak — prompting alone didn't reliably solve any of these three.
