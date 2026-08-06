import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
from pydantic import BaseModel, Field, ValidationError

from utils.groq_client import call_groq_with_retry, truncate_text

logger = logging.getLogger(__name__)

class ProductItem(BaseModel):
    product_name: str = Field(..., description="The name of the product. This field is required and cannot be empty.")
    sku: Optional[str] = Field(None, description="The SKU (Stock Keeping Unit) identifier. Optional.")
    price: float = Field(..., description="The numeric price of the product, stripped of currency symbols like $, €, £. Required.")
    category: str = Field("Uncategorized", description="The category classification. Falls back to 'Uncategorized' if not found or missing.")
    specifications: List[str] = Field(default_factory=list, description="A list of technical specifications, sizes, attributes, or features.")
    in_stock: Optional[bool] = Field(None, description="Availability status (True if in stock/available, False if out of stock). Optional.")

class ExtractedProductData(BaseModel):
    products: List[ProductItem] = Field(..., description="List of extracted products from the document.")

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extracts text page by page from raw PDF bytes using PyMuPDF (fitz).
    """
    if not pdf_bytes:
        raise ValueError("The uploaded PDF file is empty.")
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if len(doc) == 0:
            raise ValueError("The uploaded PDF contains no pages.")
        full_text = []
        for page_num, page in enumerate(doc):
            text = page.get_text()
            full_text.append(f"--- PAGE {page_num + 1} ---\n{text}")
        return "\n".join(full_text)
    except Exception as e:
        logger.error(f"Error reading PDF bytes: {e}")
        if "no pages" in str(e) or "empty" in str(e):
            raise e
        raise ValueError(f"Failed to parse PDF document. It may be corrupt or invalid. Error: {str(e)}")

def extract_products_from_text(
    text: str, 
    api_key: Optional[str] = None, 
    model: str = "llama-3.3-70b-versatile"
) -> Dict[str, Any]:
    """
    Sends the PDF raw text content to Groq using JSON Mode.
    Instructs the LLM to extract product attributes according to the Pydantic schema.
    """
    truncated_text = truncate_text(text, max_chars=35000)
    
    system_prompt = (
        "You are an expert product data extraction assistant. "
        "Your task is to analyze raw text/tables extracted from product catalog sheets, invoices, or specifications brochures "
        "and extract all identifiable products into a strict JSON payload format. "
        "You must return a JSON object containing a 'products' key, which maps to a list of products. "
        "Each product object in the list must conform to the following JSON schema:\n"
        "{\n"
        "  'product_name': string (required),\n"
        "  'sku': string (optional, null if not found),\n"
        "  'price': number (float, required, strip any currency symbols, e.g. '$129.99' -> 129.99),\n"
        "  'category': string (required, fallback to 'Uncategorized' if not specified),\n"
        "  'specifications': array of strings (required, list of key features/specs, default to empty list []),\n"
        "  'in_stock': boolean (optional, true/false/null)\n"
        "}\n"
        "Only output valid JSON. Do not include markdown wraps (like ```json ... ```) or conversational commentary."
    )

    prompt = (
        f"Here is the raw text extracted from the document:\n\n"
        f"--- START DOCUMENT ---\n"
        f"{truncated_text}\n"
        f"--- END DOCUMENT ---\n\n"
        f"Extract all products and generate the conforming JSON object."
    )

    response_text = call_groq_with_retry(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        api_key=api_key,
        json_mode=True,
        temperature=0.1  # Low temperature for high extraction fidelity
    )

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response from Groq: {response_text}. Error: {e}")
        # Return a dictionary wrapping the error so the UI can handle it
        raise ValueError(f"Groq did not return valid JSON: {str(e)}. Raw response: {response_text}")

def validate_extracted_products(raw_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Validates a raw JSON payload extracted from Groq against the Pydantic schema.
    Returns detailed validation records indicating pass/fail status and specific error reasons.
    """
    validated_records = []
    
    # Handle direct dict fallback or wrapping list
    products_list = raw_json.get("products")
    if products_list is None:
        if "product_name" in raw_json:
            products_list = [raw_json]
        else:
            products_list = []
            
    if not isinstance(products_list, list):
        products_list = []

    for idx, item in enumerate(products_list):
        if not isinstance(item, dict):
            validated_records.append({
                "index": idx,
                "data": item,
                "is_valid": False,
                "errors": ["Product item is not a valid JSON object"],
                "validated_object": None
            })
            continue

        try:
            # Let's perform slight pre-cleaning to strip currencies or convert numbers if they are strings
            cleaned_item = item.copy()
            
            # Clean price string if LLM returned string price despite description
            if "price" in cleaned_item and isinstance(cleaned_item["price"], str):
                price_str = cleaned_item["price"]
                # Strip out currencies and common characters
                for char in ["$", "€", "£", ",", " "]:
                    price_str = price_str.replace(char, "")
                try:
                    cleaned_item["price"] = float(price_str)
                except ValueError:
                    pass # Let Pydantic throw the type validation error
            
            product_obj = ProductItem(**cleaned_item)
            validated_records.append({
                "index": idx,
                "data": cleaned_item,
                "is_valid": True,
                "errors": [],
                "validated_object": product_obj
            })
        except ValidationError as e:
            errors = []
            for error in e.errors():
                loc = " -> ".join(str(x) for x in error["loc"])
                msg = error["msg"]
                errors.append(f"Field '{loc}': {msg}")
            
            validated_records.append({
                "index": idx,
                "data": item,
                "is_valid": False,
                "errors": errors,
                "validated_object": None
            })
            
    return validated_records
