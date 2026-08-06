# Decision Log — Track B (AI Workflow and Validation)

Three decisions I made while building this, why I picked what I picked, and what I said no to.

---

## Decision 1: How I chunk documents for the Founder Brief

The brief generator has to take a few source docs and produce a short brief where I can actually point to which sentence a claim came from. I didn't want to just throw whole documents at the LLM and hope it cites correctly — that's hard to verify after the fact, and it's slower/more expensive on bigger inputs.

I thought about splitting documents "properly" — by headings, page breaks, that kind of layout-aware splitting. It's more accurate in theory but I didn't have time to build/test that reliably, and it adds dependencies I didn't want to deal with in a 6-hour window.

So I went simpler: a fixed character sliding window (1000 chars, 150 overlap). It's dumb and will cut mid-sentence sometimes. To fix that, I wrote a fuzzy word-overlap matcher (`find_best_sentence_match`) that takes whatever the model claims and matches it back to the real sentence in the source. Basically — cheap chunking, but I put the verification effort into checking the output instead of perfecting the input split.

---

## Decision 2: How I stop the email drafter from making stuff up

This was the one I was most worried about — an email going out with a made-up date or number would be a real failure, not a cosmetic one.

First instinct was to have the LLM check its own draft with a second prompt. Tried that mentally and didn't like it — if the model hallucinated once, there's no guarantee a second pass from the same model catches it. Same blind spot, twice.

The other option was to skip the LLM for anything factual and just template the email. That's bulletproof but reads robotic, and defeats the point of using AI here.

What I ended up doing: let the LLM draft the email normally, then run the draft through a plain Python check (`verify_email_facts`) that pulls out proper nouns, numbers, and dates and compares them against the actual input JSON. Anything in the draft that isn't traceable to the source data gets flagged. I had to add a small ignore-list (`COMMON_IGNORES`) because it was flagging normal words like "Dear" and "Monday" as unverified at first.

---

## Decision 3: How I validate the messy PDF extraction

The PDFs I'm parsing are intentionally messy, so getting clean structured data out isn't trivial.

I first tried leaning purely on prompt instructions to force the right JSON shape — didn't hold up well on messier inputs, kept getting malformed output. Pure regex was the other option but it broke every time the layout shifted slightly, which happens a lot with these files.

Landed on: Groq JSON mode at a low temperature (0.1) so the output stays consistent, plus a Pydantic schema (`ProductItem`) to catch anything that's still wrong shape-wise. I still had to add manual pre-cleaning (stripping currency symbols before converting to float) because telling the model "output clean numbers" in the prompt wasn't reliable enough on its own — it would still leave a ₹ or $ in there sometimes.

---

**Overall pattern across all three:** I didn't fully trust the model on any of these — chunking, email facts, or number formatting — so each one has a small deterministic check sitting after the AI step rather than trusting the AI output directly.
