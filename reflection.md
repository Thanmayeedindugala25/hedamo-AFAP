# Reflection

## Time log

| Task | Time spent |
|---|---|
| HEDAMO diagnostic — verification | ~30 min |
| HEDAMO diagnostic — writing the high-level brief | ~10–15 min |
| Track B build (PDF extractor, brief generator, email drafter, API integration) | ~3 hrs |
| Testing, validation, fixing issues | rest of the time, within the guide |

I stayed within the time guide overall. What I didn't get to: further UI polish and making the interface more effective — I made a call to stop there rather than keep iterating past the guide.

## What challenged me most

The citation/chunking logic in the Founder Brief generator was the hardest part. My first version didn't work well — the brief generator and the email drafter both failed early on, mainly because I was passing things between the three components (extraction, brief generation, email drafting) without a clear enough separation, and I ended up confusing myself about which task fed into which. It took a bit to realize the three tasks needed cleaner boundaries and interfaces rather than being loosely connected.

I also ran into API usage becoming a real constraint — every iteration during testing costs a call, so I added the API integration directly into the UI (model selection, key entry) partly to make it usable, and that also forced me to be more deliberate about testing instead of brute-force re-running things, which helped.

## What failed, and what I did about it

- The Founder Brief and email generator both failed in early versions — traced back to unclear interlinking between the three components rather than a single obvious bug.
- Once I separated the concerns more cleanly (each component doing one job, with defined inputs/outputs), both started working reliably.
- Testing (documented in `evidence/verification.md`) later surfaced two more specific failures I hadn't caught by eye: a Pydantic schema gap on a legitimately-missing price field, and a false-positive flag in the email fact-gate on a normal capitalized word. Both are documented there rather than quietly fixed, since I ran out of time to properly test the fix.

## What I'd automate or change next

- Fix the two documented gaps: make `price` optional in the extraction schema, and replace the fixed `COMMON_IGNORES` word list with a general rule for sentence-initial capitalization.
- Spend more time on the UI to make the workflow more user-friendly — right now it's functional but not particularly guided for a first-time user.
- Test more edge cases across all three components (not just the ones in this sample set) to find more limitations before they show up in real use.

## With one more day

I'd use it mostly on testing, not new features — running each component against a wider, messier set of inputs to surface more failure modes like the two I found, fixing them, and re-testing. I'd also clean up the UI so someone unfamiliar with the tool could use it without me explaining it first.
