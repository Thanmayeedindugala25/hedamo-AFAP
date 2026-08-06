# AI Document Intelligence & Validation Toolkit

A modular, production-ready Streamlit application that provides structured data extraction, executive synthesis with verifiable chunk-level citations, and fact-gated recruiting email generation.

## Features

- **Messy PDF Product Extractor**: Parses unstructured or messy PDF documents (like catalogs and invoices), maps the data, and validates it against a strict Pydantic schema (product name, SKU, price, category, stock availability, and specifications). Includes a JSON payload viewer and download option.
- **Cited Founder Brief Generator**: Indexes up to 5 source documents (PDF or TXT), splits them into deterministic chunks with unique IDs, and synthesizes an executive brief using Groq. Includes an interactive inspection panel to trace, highlight, and audit citations at the sentence level.
- **Fact-Gated Candidate Email Drafter**: Drafts personalized recruiter emails based on candidate attributes and feedback notes. Uses a deterministic verification layer (Fact-Gate Guardrail) to intercept drafts and check for hallucinations (like unlisted numbers, dates, or named entities).

## Folder Structure

```
├── .streamlit/
│   └── config.toml          # Streamlit theme configuration
├── sample_data/             # Synthetic test files for demo verification
│   ├── messy_catalog_1.pdf
│   ├── messy_catalog_2.pdf
│   ├── messy_catalog_3.pdf
│   ├── founder_doc_1.txt
│   ├── founder_doc_2.txt
│   ├── founder_doc_3.txt
│   ├── founder_doc_4.txt
│   ├── founder_doc_5.txt
│   └── candidate_data.json
├── utils/
│   ├── brief_generator.py   # Text chunking, brief synthesis, fuzzy sentence alignment
│   ├── email_drafter.py     # Email drafting, deterministic fact-checking logic
│   ├── groq_client.py       # Groq client initialization, retry & backoff mechanism
│   └── pdf_extractor.py     # PDF text extraction, Pydantic schema validation
├── .env.example             # Template for API credentials
├── app.py                   # Main Streamlit application and layout
└── requirements.txt         # Project dependencies
```

## Installation

1. Clone or copy the project files to your workspace directory.
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Environment Variables

Copy `.env.example` to `.env` and provide your Groq API key:
```env
GROQ_API_KEY=your_api_key_here
```
*(Alternatively, you can provide the Groq API key directly via the sidebar in the running application).*

## Running the App

Start the Streamlit application from the root directory:
```bash
streamlit run app.py
```
Open the provided local URL (typically `http://localhost:8501`) in your browser.

## Technologies Used

- **Streamlit**: Web application framework.
- **Groq Python SDK**: Inference engine for high-speed LLM processing.
- **PyMuPDF (fitz)**: PDF document text extraction.
- **Pydantic v2**: Strict schema definition and runtime object validation.
- **python-dotenv**: Environment variable management.

## Known Limitations

- **Text Extraction Bounds**: Relies on selectable text within PDFs. Scanned or rasterized images of documents require OCR preprocessing, which is not supported natively.
- **Deterministic Matcher Sensitivity**: The Email Drafter's proper noun/number verification is strictly deterministic and may flag false positives on common nouns or formatting differences if they are capitalized or structured unexpectedly.
