import streamlit as st
import json
import os
import re
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Import helper functions
from utils.pdf_extractor import (
    extract_text_from_pdf_bytes,
    extract_products_from_text,
    validate_extracted_products
)
from utils.brief_generator import (
    extract_text_from_file_bytes,
    chunk_text,
    generate_founder_brief,
    extract_citations_from_text,
    find_best_sentence_match
)
from utils.email_drafter import (
    draft_candidate_email,
    verify_email_facts
)

# Page configuration
st.set_page_config(
    page_title="AI Doc Intel & Validation Toolkit",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom Google Fonts and custom CSS for high-end aesthetics
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    /* Apply globally */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6, .main-title {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700;
    }
    
    /* Title styling */
    .main-title {
        background: linear-gradient(135deg, #a855f7 0%, #6366f1 50%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.2rem;
        padding-top: 10px;
    }
    
    .main-subtitle {
        text-align: center;
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Card Glassmorphism effect */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.15);
    }
    
    /* Card header gradients */
    .product-header-valid {
        border-left: 4px solid #10b981;
        padding-left: 10px;
        margin-bottom: 8px;
    }
    
    .product-header-invalid {
        border-left: 4px solid #ef4444;
        padding-left: 10px;
        margin-bottom: 8px;
    }
    
    /* Badges */
    .badge-category {
        background: rgba(99, 102, 241, 0.15);
        color: #818cf8;
        border: 1px solid rgba(99, 102, 241, 0.3);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 5px;
        display: inline-block;
    }
    
    .badge-price {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 5px;
        display: inline-block;
    }
    
    .badge-sku {
        background: rgba(245, 158, 11 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 5px;
        display: inline-block;
    }
    
    .badge-stock {
        background: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.3);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 5px;
        display: inline-block;
    }
    
    .badge-out-of-stock {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 5px;
        display: inline-block;
    }
    
    /* Error item */
    .error-list {
        background: rgba(239, 68, 68, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.2);
        color: #f87171;
        padding: 10px 15px;
        border-radius: 8px;
        font-size: 0.85rem;
        margin-top: 10px;
    }
    
    /* Highlighted sentence citation */
    .highlighted-sentence {
        background: rgba(168, 85, 247, 0.25);
        border-bottom: 2px solid #a855f7;
        color: #e9d5ff;
        padding: 1px 3px;
        border-radius: 3px;
        font-weight: 500;
    }
    
    /* Citation pills in brief list */
    .citation-pill {
        color: #a855f7;
        font-weight: 600;
        cursor: pointer;
        background: rgba(168, 85, 247, 0.1);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.85em;
        border: 1px solid rgba(168, 85, 247, 0.3);
    }
    
    /* Factual accuracy container */
    .fact-gate-passed {
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-left: 5px solid #10b981;
        border-radius: 8px;
        padding: 15px;
        color: #34d399;
        margin-bottom: 15px;
    }
    
    .fact-gate-failed {
        background: rgba(239, 68, 68, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-left: 5px solid #ef4444;
        border-radius: 8px;
        padding: 15px;
        color: #f87171;
        margin-bottom: 15px;
    }
    
    .infringement-item {
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.2);
        color: #fbbf24;
        padding: 8px 12px;
        border-radius: 6px;
        margin-top: 6px;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Header Title & Description
st.markdown('<div class="main-title">AI Document Intelligence & Validation</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">Modular Production-Grade Document Extraction, Citation Verification, & Fact-Gated Drafting</div>', unsafe_allow_html=True)

# ----------------- SIDEBAR CONFIGURATION -----------------
st.sidebar.markdown('<div class="sidebar-title">🛡️ System Control Panel</div>', unsafe_allow_html=True)

# API Key settings
env_key = os.getenv("GROQ_API_KEY", "")
api_key_input = st.sidebar.text_input(
    "Groq API Key",
    type="password",
    value=env_key if env_key else "",
    placeholder="gsk_..." if not env_key else "Loaded from .env",
    help="Enter your Groq API Key. If empty, the app defaults to the system .env key."
)
groq_key = api_key_input if api_key_input else env_key

# Model Selection
model_selection = st.sidebar.selectbox(
    "Primary Model Selection",
    [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it"
    ],
    index=0,
    help="Default recommended model: llama-3.3-70b-versatile"
)

st.sidebar.divider()
st.sidebar.markdown(
    """
    **Application Modules:**
    1. **Product Extractor**: Strict validation of messy tables/text into verified JSON.
    2. **Cited Founder Brief**: Index documents, split chunks, synthesize brief, inspect sources.
    3. **Email Drafter**: Form input + deterministic gate logic to prevent hallucinations.
    """
)

# Create main Streamlit Tabs
tab1, tab2, tab3 = st.tabs([
    "📦 Messy PDF Product Extractor", 
    "📝 Cited Founder Brief Generator", 
    "📧 Fact-Gated Candidate Email Drafter"
])

# Helper check for API Key
def check_key():
    if not groq_key:
        st.error("⚠️ Groq API key is missing. Please add it to the sidebar input or create a `.env` file containing `GROQ_API_KEY`.")
        return False
    return True

# ----------------- TAB 1: PRODUCT EXTRACTOR -----------------
with tab1:
    st.header("Upload Messy Product Catalogs")
    st.write("Upload up to 3 PDFs containing product lists, specifications, or invoices. The engine will extract the catalog items, run structured parsing, and perform post-extraction validation against our strict schema.")
    
    uploaded_pdfs = st.file_uploader(
        "Select PDF Catalogs",
        type=["pdf"],
        accept_multiple_files=True,
        key="pdf_uploader"
    )
    
    if uploaded_pdfs:
        if len(uploaded_pdfs) > 3:
            st.warning("⚠️ Maximum upload limit is 3 PDFs simultaneously. Excess documents will be ignored.")
            uploaded_pdfs = uploaded_pdfs[:3]
            
    extract_btn = st.button("🚀 Extract & Validate Product Catalog", use_container_width=True)
    
    # Session State storage for Tab 1
    if "extracted_products_data" not in st.session_state:
        st.session_state["extracted_products_data"] = None
        st.session_state["extracted_raw_json"] = None

    if extract_btn:
        if not uploaded_pdfs:
            st.warning("⚠️ Please upload at least one PDF catalog file first.")
        elif check_key():
            with st.spinner("Extracting text and structure from uploaded PDFs..."):
                combined_text = ""
                has_error = False
                for idx, pdf in enumerate(uploaded_pdfs):
                    try:
                        pdf_bytes = pdf.read()
                        pdf.seek(0)  # Reset pointer for subsequent reads
                        extracted_text = extract_text_from_pdf_bytes(pdf_bytes)
                        combined_text += f"\n\n--- DOCUMENT {idx + 1}: {pdf.name} ---\n{extracted_text}"
                    except Exception as e:
                        st.error(f"Error parsing PDF '{pdf.name}': {str(e)}")
                        has_error = True
                
                if not has_error:
                    if combined_text.strip():
                        with st.spinner("Analyzing text with Groq and formatting structure..."):
                            try:
                                # 1. API Call (JSON Mode)
                                raw_json = extract_products_from_text(
                                    text=combined_text,
                                    api_key=groq_key,
                                    model=model_selection
                                )
                                
                                # 2. Pydantic post-extraction validation
                                validation_results = validate_extracted_products(raw_json)
                                
                                # Store in session state
                                st.session_state["extracted_products_data"] = validation_results
                                st.session_state["extracted_raw_json"] = raw_json
                                st.toast("Product extraction completed successfully!", icon="✅")
                            except ValueError as e:
                                st.error(f"⚠️ Extraction Error: {str(e)}")
                            except Exception as e:
                                st.error(f"⚠️ An unexpected API or validation error occurred: {str(e)}")
                    else:
                        st.error("No text could be extracted from the uploaded PDFs.")
                    
    # Display results
    if st.session_state["extracted_products_data"]:
        val_results = st.session_state["extracted_products_data"]
        raw_json_obj = st.session_state["extracted_raw_json"]
        
        # Calculate health metrics
        total_items = len(val_results)
        valid_items = sum(1 for x in val_results if x["is_valid"])
        invalid_items = total_items - valid_items
        
        st.subheader("Data Extraction Summary")
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric("Total Items Extracted", total_items)
        with m_col2:
            st.metric("Passed Pydantic Validation", f"{valid_items} / {total_items}")
        with m_col3:
            health_rate = (valid_items / total_items * 100) if total_items > 0 else 0
            st.metric("Data Integrity Rating", f"{health_rate:.1f}%")
            
        st.divider()
        
        col_list, col_raw = st.columns([3, 2])
        
        with col_list:
            st.subheader("Extracted Catalog Items")
            for idx, item in enumerate(val_results):
                data = item["data"]
                is_valid = item["is_valid"]
                errors = item["errors"]
                
                card_class = "product-header-valid" if is_valid else "product-header-invalid"
                valid_icon = "🟢 Validated" if is_valid else "🔴 Validation Fail"
                
                with st.container():
                    st.markdown(f'<div class="glass-card">', unsafe_allow_html=True)
                    
                    st.markdown(
                        f'<div class="{card_class}">'
                        f'<h3 style="margin: 0; display: inline;">{data.get("product_name", "Unknown Product")}</h3> '
                        f'<span style="float: right; font-size: 0.85rem; font-weight: bold; opacity: 0.8;">{valid_icon}</span>'
                        f'</div>', 
                        unsafe_allow_html=True
                    )
                    
                    # Badges row
                    price_val = data.get("price")
                    price_display = f"${price_val:.2f}" if isinstance(price_val, (int, float)) else "N/A"
                    category_display = data.get("category", "Uncategorized")
                    sku_display = f"SKU: {data.get('sku')}" if data.get('sku') else "SKU: N/A"
                    
                    in_stock = data.get("in_stock")
                    if in_stock is True:
                        stock_badge = '<span class="badge-stock">In Stock</span>'
                    elif in_stock is False:
                        stock_badge = '<span class="badge-out-of-stock">Out of Stock</span>'
                    else:
                        stock_badge = ''
                        
                    st.markdown(
                        f'<div style="margin-bottom: 12px;">'
                        f'<span class="badge-category">{category_display}</span>'
                        f'<span class="badge-price">{price_display}</span>'
                        f'<span class="badge-sku">{sku_display}</span>'
                        f'{stock_badge}'
                        f'</div>', 
                        unsafe_allow_html=True
                    )
                    
                    # Specifications
                    specs = data.get("specifications", [])
                    if specs:
                        st.markdown("**Key Specifications:**")
                        for s in specs:
                            st.markdown(f"- {s}")
                    else:
                        st.markdown("*No specifications list found.*")
                        
                    # Error list representation
                    if not is_valid and errors:
                        st.markdown('<div class="error-list">', unsafe_allow_html=True)
                        st.markdown("**Validation Errors:**")
                        for err in errors:
                            st.markdown(f"• {err}")
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                    st.markdown('</div>', unsafe_allow_html=True)
                    
        with col_raw:
            st.subheader("Payload Output Inspector")
            st.write("Review the raw JSON object generated. Useful for direct database uploads.")
            
            # Format JSON string nicely
            formatted_json = json.dumps(raw_json_obj, indent=2)
            st.code(formatted_json, language="json")
            
            # Download JSON button
            st.download_button(
                label="📥 Download Extracted JSON",
                data=formatted_json,
                file_name="extracted_products.json",
                mime="application/json",
                use_container_width=True
            )

# ----------------- TAB 2: CITED BRIEF GENERATOR -----------------
with tab2:
    st.header("Executive Founder Brief Synthesizer")
    st.write("Upload up to 5 source documents (TXT or PDF). The system splits files into deterministic chunks, maps unique chunk IDs, and generates a structured brief citing the precise references. Use the Interactive Inspector panel to audit and trace any citation instantly.")
    
    uploaded_brief_files = st.file_uploader(
        "Upload Reference Documents",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        key="brief_uploader"
    )
    
    if uploaded_brief_files:
        if len(uploaded_brief_files) > 5:
            st.warning("⚠️ Maximum upload limit is 5 reference files simultaneously. Excess documents will be ignored.")
            uploaded_brief_files = uploaded_brief_files[:5]
            
    brief_btn = st.button("🔥 Generate Cited Founder Brief", use_container_width=True)
    
    # State management for tab 2
    if "brief_text" not in st.session_state:
        st.session_state["brief_text"] = ""
        st.session_state["brief_chunks"] = {}
        st.session_state["brief_citations"] = []
        st.session_state["raw_document_texts"] = {}

    if brief_btn:
        if not uploaded_brief_files:
            st.warning("⚠️ Please upload at least one reference document first.")
        elif check_key():
            with st.spinner("Splitting source documents into indexed chunks..."):
                all_chunks = []
                doc_texts = {}
                has_error = False
                
                for idx, doc_file in enumerate(uploaded_brief_files):
                    try:
                        doc_index = idx + 1
                        file_bytes = doc_file.read()
                        doc_file.seek(0)  # Reset pointer for subsequent reads
                        raw_text = extract_text_from_file_bytes(file_bytes, doc_file.name)
                        doc_texts[doc_file.name] = raw_text
                        
                        # Chunk the document text
                        chunks = chunk_text(raw_text, doc_index, doc_file.name)
                        all_chunks.extend(chunks)
                    except Exception as e:
                        st.error(f"Error indexing '{doc_file.name}': {str(e)}")
                        has_error = True
                        
                if not has_error:
                    if all_chunks:
                        # Save to mapping store
                        chunks_map = {c["id"]: c for c in all_chunks}
                        st.session_state["brief_chunks"] = chunks_map
                        st.session_state["raw_document_texts"] = doc_texts
                        
                        with st.spinner("Synthesizing citations and drafting brief..."):
                            try:
                                brief_result = generate_founder_brief(
                                    all_chunks=all_chunks,
                                    api_key=groq_key,
                                    model=model_selection
                                )
                                st.session_state["brief_text"] = brief_result
                                st.session_state["brief_citations"] = extract_citations_from_text(brief_result)
                                st.toast("Founder Brief generated successfully!", icon="📝")
                            except ValueError as e:
                                st.error(f"⚠️ Synthesis Error: {str(e)}")
                            except Exception as e:
                                st.error(f"⚠️ Failed to generate brief: {str(e)}")
                    else:
                        st.error("No content could be processed from the uploaded documents.")

    # UI presentation of the brief and inspector
    if st.session_state["brief_text"]:
        col_brief, col_inspector = st.columns([3, 2])
        
        with col_brief:
            st.subheader("Synthesized Founder Brief")
            st.write("Scroll and read the brief. Notice the bracketed citations (e.g., `[DOC1_CHUNK_02]`).")
            
            # Format citation links in markdown to stand out
            formatted_brief = st.session_state["brief_text"]
            
            # Show markdown
            st.markdown(formatted_brief)
            
            st.divider()
            st.subheader("Available Chunks Index")
            with st.expander("🔍 View All Chunk Details"):
                for cid, chunk in st.session_state["brief_chunks"].items():
                    st.markdown(f"**{cid}** (Source: `{chunk['doc_name']}`)")
                    st.text_area(f"Content for {cid}", chunk["text"][:300] + "...", height=100, disabled=True)
                    
        with col_inspector:
            st.subheader("🔍 Citation Source Inspector")
            st.write("Select a citation tag present in the brief. The tool will trace it back, retrieve the original document segment, and highlight the most relevant context.")
            
            cits = st.session_state["brief_citations"]
            if not cits:
                st.info("No citation tags matched. Check the brief for format `[DOCx_CHUNK_y]`.")
            else:
                selected_cit = st.selectbox(
                    "Select Citation ID to Audit:",
                    cits,
                    help="Matches citation tags found within the brief."
                )
                
                if selected_cit and selected_cit in st.session_state["brief_chunks"]:
                    chunk = st.session_state["brief_chunks"][selected_cit]
                    st.markdown(f"**Source Document:** `{chunk['doc_name']}`")
                    st.markdown(f"**Chunk Reference:** `{chunk['id']}`")
                    
                    # Highlight sentences
                    # Find all sentences in the brief that contain the citation
                    brief_text_raw = st.session_state["brief_text"]
                    citing_sentences = []
                    # Split brief into sentences and check for presence of citation
                    raw_sentences = re.split(r'(?<=[.!?])\s+', brief_text_raw)
                    for sen in raw_sentences:
                        if selected_cit in sen:
                            citing_sentences.append(sen)
                            
                    # Find best sentence match in the original chunk text
                    best_match_sen, pos = find_best_sentence_match(chunk["text"], citing_sentences)
                    
                    st.markdown("**Original Source Passage:**")
                    if best_match_sen and pos != -1:
                        # Highlight the matched sentence in the chunk
                        highlighted_chunk = (
                            chunk["text"][:pos] + 
                            f'<mark class="highlighted-sentence">{best_match_sen}</mark>' + 
                            chunk["text"][pos + len(best_match_sen):]
                        )
                        st.markdown(
                            f'<div style="background: rgba(255,255,255,0.02); padding: 15px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); line-height: 1.6; max-height: 400px; overflow-y: auto;">'
                            f'{highlighted_chunk}'
                            f'</div>', 
                            unsafe_allow_html=True
                        )
                        st.caption("✨ purple highlights correspond to sentence-level textual alignment.")
                    else:
                        st.markdown(
                            f'<div style="background: rgba(255,255,255,0.02); padding: 15px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); line-height: 1.6;">'
                            f'{chunk["text"]}'
                            f'</div>', 
                            unsafe_allow_html=True
                        )

# ----------------- TAB 3: EMAIL DRAFTER -----------------
with tab3:
    st.header("Fact-Gated Candidate Email Drafter")
    st.write("Enter candidate interview attributes. The engine will draft a personalized follow-up email. A deterministic validation layer intercepts the email draft and checks for any hallucinated details (like salaries or interview dates) not provided in the input payload.")
    
    input_method = st.radio("Choose Input Mode", ["Form UI Builder", "Raw JSON Input"], horizontal=True)
    
    input_payload = {}
    
    if input_method == "Form UI Builder":
        e_col1, e_col2 = st.columns(2)
        with e_col1:
            c_name = st.text_input("Candidate Name", value="Alexander Chen")
            pos_applied = st.text_input("Position Applied", value="Senior ML Research Engineer")
            int_status = st.selectbox("Interview Status", ["Accepted", "Rejected", "Next Round"], index=2)
            
        with e_col2:
            include_date = st.checkbox("Specify Interview/Feedback Date", value=True)
            if include_date:
                int_date = st.date_input("Interview / Next Step Date")
                date_str = str(int_date)
            else:
                date_str = None
                
            raw_notes = st.text_area(
                "Feedback Notes (One note per line)", 
                value="Deep knowledge of transformers and model execution graph optimizations.\nExcellent communication skills during the system design round.\nRequests remote work flexibility."
            )
            notes_list = [n.strip() for n in raw_notes.split("\n") if n.strip()]
            
        input_payload = {
            "candidate_name": c_name,
            "position_applied": pos_applied,
            "interview_status": int_status,
            "interview_date": date_str,
            "notes": notes_list
        }
    else:
        st.write("Paste your raw JSON payload below:")
        default_json = {
            "candidate_name": "Alexander Chen",
            "position_applied": "Senior ML Research Engineer",
            "interview_status": "Next Round",
            "interview_date": "2026-08-10",
            "notes": [
                "Deep knowledge of transformers and model execution graph optimizations.",
                "Excellent communication skills during the system design round.",
                "Requests remote work flexibility."
            ]
        }
        json_payload_str = st.text_area("JSON Payload Input", value=json.dumps(default_json, indent=2), height=250)
        try:
            input_payload = json.loads(json_payload_str)
        except json.JSONDecodeError:
            st.error("⚠️ Invalid JSON syntax. Please verify your entries.")
            input_payload = None
            
    draft_btn = st.button("📧 Generate Factual Candidate Email", use_container_width=True)
    
    # State storage for Tab 3
    if "email_subject" not in st.session_state:
        st.session_state["email_subject"] = ""
        st.session_state["email_body"] = ""
        st.session_state["validation_gate"] = None

    if draft_btn:
        if not input_payload:
            st.warning("⚠️ Please provide a valid candidate input payload first.")
        elif check_key():
            with st.spinner("Drafting candidate email with zero-hallucination instruction..."):
                try:
                    # 1. Draft using LLM with temperature = 0
                    draft = draft_candidate_email(
                        payload=input_payload,
                        api_key=groq_key,
                        model=model_selection
                    )
                    
                    # 2. Perform validation checks
                    sub = draft.get("subject", "")
                    body = draft.get("body", "")
                    
                    v_res = verify_email_facts(sub, body, input_payload)
                    
                    st.session_state["email_subject"] = sub
                    st.session_state["email_body"] = body
                    st.session_state["validation_gate"] = v_res
                    st.toast("Candidate email drafted and fact-checked!", icon="📧")
                except ValueError as e:
                    st.error(f"⚠️ Email Drafting Error: {str(e)}")
                except Exception as e:
                    st.error(f"⚠️ An unexpected error occurred: {str(e)}")

    # Display Email outputs and gate results
    if st.session_state["email_subject"]:
        st.divider()
        col_email, col_gate = st.columns([3, 2])
        
        with col_email:
            st.subheader("Generated Email Draft")
            
            st.text_input("Subject Line", value=st.session_state["email_subject"], disabled=True)
            st.text_area("Email Body", value=st.session_state["email_body"], height=300, disabled=True)
            
            # Simple native text block with copy icon
            st.caption("📋 Copy Email text below:")
            full_email_text = f"Subject: {st.session_state['email_subject']}\n\n{st.session_state['email_body']}"
            st.code(full_email_text, language="text")
            
            # Download Email Button
            st.download_button(
                label="📥 Download Email Text",
                data=full_email_text,
                file_name="candidate_email.txt",
                mime="text/plain",
                use_container_width=True
            )
            
        with col_gate:
            st.subheader("🛡️ Fact-Gate Guardrail Status")
            st.write("Deterministic analysis comparing generated entities, dates, and currency values against user-provided parameters.")
            
            gate = st.session_state["validation_gate"]
            if gate:
                if gate["is_valid"]:
                    st.markdown(
                        '<div class="fact-gate-passed">'
                        '<h4>✓ Fact-Gate Status: PASSED</h4>'
                        '<p style="margin: 0; font-size: 0.9rem;">The draft matches the input facts. No unauthorized salaries, dates, or named entities were detected.</p>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        '<div class="fact-gate-failed">'
                        '<h4>⚠️ Fact-Gate Status: WARNING</h4>'
                        '<p style="margin: 0; font-size: 0.9rem;">Potential fact infringement detected! The generated email contains terms, numbers, or dates not matching input parameters.</p>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                    
                    st.write("**Flagged Infringements:**")
                    for inf in gate["infringements"]:
                        st.markdown(
                            f'<div class="infringement-item">'
                            f'<strong>[{inf["type"]}]</strong>: {inf["message"]}'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                        
                    st.caption("⚠️ Please review and modify the email body to eliminate the flagged items before communicating with the candidate.")
