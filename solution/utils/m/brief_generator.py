import re
import logging
from typing import List, Dict, Any, Tuple, Optional
import fitz  # PyMuPDF

from utils.groq_client import call_groq_with_retry

logger = logging.getLogger(__name__)

def extract_text_from_file_bytes(file_bytes: bytes, file_name: str) -> str:
    """
    Extracts text from PDF or TXT bytes based on file extension.
    """
    if not file_bytes:
        raise ValueError(f"The uploaded file '{file_name}' is empty.")
    if file_name.lower().endswith(".pdf"):
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            if len(doc) == 0:
                raise ValueError(f"The uploaded PDF '{file_name}' contains no pages.")
            full_text = []
            for page in doc:
                full_text.append(page.get_text())
            return "\n".join(full_text)
        except Exception as e:
            logger.error(f"Error parsing PDF file {file_name}: {e}")
            if "no pages" in str(e):
                raise e
            raise ValueError(f"Could not parse PDF '{file_name}': {str(e)}")
    else:
        # Assume plain text
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                # Try latin-1 fallback
                return file_bytes.decode("latin-1")
            except Exception as e:
                logger.error(f"Error decoding text file {file_name}: {e}")
                raise ValueError(f"Could not decode text file '{file_name}': {str(e)}")

def chunk_text(text: str, doc_index: int, file_name: str, chunk_size: int = 1000, overlap: int = 150) -> List[Dict[str, Any]]:
    """
    Splits text into deterministic, overlapping chunks.
    Assigns each chunk a unique identifier, e.g. [DOC1_CHUNK_01].
    """
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    chunks = []
    text_len = len(text)
    start = 0
    chunk_num = 1
    
    if text_len == 0:
        return []
        
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk_text_data = text[start:end]
        
        chunk_id = f"[DOC{doc_index}_CHUNK_{chunk_num:02d}]"
        chunks.append({
            "id": chunk_id,
            "text": chunk_text_data,
            "doc_index": doc_index,
            "doc_name": file_name,
            "start_char": start,
            "end_char": end
        })
        
        if end == text_len:
            break
            
        start += (chunk_size - overlap)
        chunk_num += 1
        
    return chunks

def generate_founder_brief(
    all_chunks: List[Dict[str, Any]], 
    api_key: Optional[str] = None, 
    model: str = "llama-3.3-70b-versatile"
) -> str:
    """
    Sends the indexed chunk content to Groq and requests a Founder Brief.
    Includes strict instructions to cite specific source chunk IDs.
    """
    # Format chunks for context payload
    context_parts = []
    for chunk in all_chunks:
        context_parts.append(
            f"--- START CHUNK {chunk['id']} (Source: {chunk['doc_name']}) ---\n"
            f"{chunk['text']}\n"
            f"--- END CHUNK {chunk['id']} ---\n"
        )
    
    context_str = "\n".join(context_parts)
    
    system_prompt = (
        "You are an elite business analyst and executive advisor. Your task is to write a highly professional, "
        "evidence-backed Founder Brief based *only* on the provided document chunks.\n\n"
        "The Founder Brief must follow this exact Markdown structure:\n"
        "# Executive Summary\n"
        "[A summary of the core themes, findings, and situation description. Do not include chunk citations in the Executive Summary.]\n\n"
        "# Key Takeaways\n"
        "[Bullet points detailing major facts, discoveries, or statements from the documents. "
        "Every single takeaway bullet MUST end with one or more citations of the chunk(s) it came from, "
        "formatted precisely as [DOCx_CHUNK_y], e.g., '[DOC1_CHUNK_03]'.]\n\n"
        "# Market & Operational Risks\n"
        "[Bullet points describing specific threats, risks, challenges, or pitfalls raised. "
        "Every single risk bullet MUST end with one or more citations of the source chunk(s), e.g., '[DOC2_CHUNK_01]'.]\n\n"
        "# Strategic Next Steps\n"
        "[Actionable recommendations based on the findings. "
        "Every single next step bullet MUST end with one or more citations of the source chunk(s), e.g., '[DOC3_CHUNK_04]'.]\n\n"
        "Strict Citation Rules:\n"
        "1. Every claim in 'Key Takeaways', 'Market & Operational Risks', and 'Strategic Next Steps' must cite the chunk it is sourced from.\n"
        "2. Do not generalize without citing. Do not fabricate facts that are not explicitly present in the chunks.\n"
        "3. Only use the provided chunk IDs (e.g. [DOC1_CHUNK_01]). Do not invent new citation IDs."
    )

    prompt = (
        f"Here are the chunked document contexts:\n\n"
        f"{context_str}\n\n"
        f"Generate the Founder Brief according to the system prompt guidelines."
    )

    # Let's run generating brief using Groq client
    response = call_groq_with_retry(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        api_key=api_key,
        temperature=0.2  # Lower temp to stick closely to the facts
    )
    
    return response

def extract_citations_from_text(brief_text: str) -> List[str]:
    """
    Finds all citation tags like [DOC1_CHUNK_02] present in the generated brief.
    """
    citations = re.findall(r'\[DOC\d+_CHUNK_\d+\]', brief_text)
    # Return unique sorted citations
    return sorted(list(set(citations)))

def find_best_sentence_match(chunk_text: str, brief_sentences: List[str]) -> Tuple[str, int]:
    """
    Fuzzy overlaps brief sentences containing a citation with sentences in the source chunk.
    Returns the sentence in the chunk that has the maximum overlap, and its starting index.
    """
    # Split chunk into sentences
    chunk_sentences = re.split(r'(?<=[.!?]) +', chunk_text)
    
    best_match = ""
    max_overlap_score = 0
    
    # Simple clean tokenizer
    def get_words(s: str) -> set:
        return set(re.findall(r'\b\w{3,}\b', s.lower())) # only words length >= 3

    brief_words = set()
    for s in brief_sentences:
        brief_words.update(get_words(s))
        
    if not brief_words:
        return "", -1
        
    for sentence in chunk_sentences:
        sentence_words = get_words(sentence)
        overlap = len(brief_words.intersection(sentence_words))
        if overlap > max_overlap_score:
            max_overlap_score = overlap
            best_match = sentence
            
    # Find position of best match sentence in the chunk text
    if best_match:
        pos = chunk_text.find(best_match)
        return best_match, pos
        
    return "", -1
