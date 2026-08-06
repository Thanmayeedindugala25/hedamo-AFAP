# Demo

**[Watch the demo (Google Drive, ~2 min)](https://drive.google.com/file/d/1kRB_-GzdYPzDdmhKMkn46MIGv-rKOm8K/view?usp=sharing)**

The video shows all three Track B modules running live against the sample data in `evidence/sample_inputs/`:

1. **Product Extractor** — uploading the 3 messy PDFs and showing the Data Extraction Summary (7 items extracted, 6/7 passed strict Pydantic validation).
2. **Founder Brief Generator** — uploading the 5 source docs and showing the generated brief with citations traceable back to source.
3. **Email Drafter** — loading the candidate JSON and showing the generated email, including the Fact-Gate warning flagging "Additionally" as a false positive.

Corresponding written detail, metrics, and the two documented failure cases are in [`../verification.md`](../verification.md).
