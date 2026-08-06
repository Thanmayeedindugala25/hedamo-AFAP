import re
import json
import logging
from typing import Dict, Any, List, Optional, Set

from utils.groq_client import call_groq_with_retry

logger = logging.getLogger(__name__)

# Common English words and recruitment terms to ignore for proper noun checks
COMMON_IGNORES = {
    "We", "You", "Thank", "Dear", "I", "The", "If", "Please", "In", "As", "Our", 
    "At", "On", "By", "For", "This", "That", "Next", "Accepted", "Rejected", 
    "Round", "Interview", "Status", "Position", "Date", "Notes", "Hello", "Hi", 
    "Best", "Sincerely", "Regard", "Regards", "With", "Here", "Your", "To", 
    "From", "Would", "Should", "Could", "Will", "Shall", "Hope", "It", "They",
    "He", "She", "Us", "Thanks", "Warmly", "Warm", "Kind", "Kindest", "This", 
    "Is", "Are", "We're", "Let", "Do", "Have", "Has", "Had", "Can", "Update",
    "Invitation", "Details", "Application", "Opportunity", "Process", "Step",
    "Feedback", "Request", "Response", "Message", "Notification", "Congratulations",
    "Schedule", "Scheduling", "Email", "Subject", "Candidate", "Coordinator",
    "Manager", "Team", "Company", "Office", "Role", "Job", "Careers", "Human",
    "Resources", "Talent", "Acquisition", "Recruiting", "Recruiter", "Monday",
    "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December", "Am", "Pm", "A", "An", "And"
}

def draft_candidate_email(
    payload: Dict[str, Any],
    api_key: Optional[str] = None,
    model: str = "llama-3.3-70b-versatile"
) -> Dict[str, str]:
    """
    Drafts an email based on the input payload. Uses Groq with temperature=0.0.
    Outputs a JSON object containing "subject" and "body".
    """
    payload_str = json.dumps(payload, indent=2)
    
    system_prompt = (
        "You are an automated recruitment communications assistant.\n"
        "Your task is to write a highly professional candidate email based STRICTLY on the provided JSON data. "
        "You must output a JSON object containing exactly two keys:\n"
        "  - 'subject': A brief, professional email subject line.\n"
        "  - 'body': The full body of the email.\n\n"
        "Strict Hallucination-Proof Rules:\n"
        "1. Do not invent any names, numbers, salaries, dates, times, locations, contact info (like phone numbers/emails), or feedback that are not explicitly provided in the input JSON.\n"
        "2. If an interview date is not specified, write a polite placeholder asking the candidate for their availability; do NOT make up a date.\n"
        "3. Keep the tone warm, clear, and professional.\n"
        "4. Return ONLY the JSON object. Do not wrap in markdown syntax (```json ... ```)."
    )

    prompt = (
        f"Here is the candidate input data:\n"
        f"{payload_str}\n\n"
        f"Draft the email subject and body in JSON format."
    )

    response_text = call_groq_with_retry(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        api_key=api_key,
        json_mode=True,
        temperature=0.0  # Force maximum deterministic output
    )

    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse email drafter output as JSON: {response_text}. Error: {e}")
        raise ValueError(f"Failed to parse model response as JSON: {str(e)}")

def extract_numbers(text: str) -> List[str]:
    """
    Extracts numbers (integers or decimals, including commas/currency symbols) from text.
    Filters out short single digits (like list numbers 1, 2) to prevent false positives.
    """
    # Match numbers, optionally with currency or decimals, e.g. $120,000 or 15.5
    raw_matches = re.findall(r'\b\d+(?:,\d+)*(?:\.\d+)?\b|\b\$\d+(?:,\d+)*(?:\.\d+)?\b', text)
    cleaned = []
    for match in raw_matches:
        val = match.replace("$", "").replace(",", "")
        # Ignore simple 1-digit numbers like "1", "2" which are usually lists, unless they are decimal
        if len(val) == 1 and val.isdigit():
            continue
        cleaned.append(match)
    return list(set(cleaned))

def extract_dates(text: str) -> List[str]:
    """
    Extracts potential dates, days, and months mentioned in the email.
    """
    months = ["january", "february", "march", "april", "may", "june", 
              "july", "august", "september", "october", "november", "december",
              "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    
    found = []
    
    # Check for month names
    for m in months:
        if re.search(r'\b' + m + r'\b', text, re.IGNORECASE):
            found.append(m.capitalize())
            
    # Check for day names
    for d in days:
        if re.search(r'\b' + d + r'\b', text, re.IGNORECASE):
            found.append(d.capitalize())
            
    # Check for numeric date formats like DD/MM/YYYY, MM/DD/YYYY or YYYY-MM-DD
    date_patterns = re.findall(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b', text)
    found.extend(date_patterns)
    
    return list(set(found))

def extract_proper_nouns(text: str) -> List[str]:
    """
    Extracts sequences of capitalized words on the same line that could represent named entities.
    Avoids multi-line captures.
    """
    # Match capitalized word sequences separated by spaces or tabs on the same line
    candidates = re.findall(r'\b[A-Z][a-zA-Z0-9_]*(?:[ \t]+[A-Z][a-zA-Z0-9_]*)*\b', text)
    
    filtered = []
    for c in candidates:
        words = c.split()
        # If the phrase is just ignore words, skip
        if all(w in COMMON_IGNORES for w in words):
            continue
        filtered.append(c)
        
    return list(set(filtered))

def verify_email_facts(email_subject: str, email_body: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs deterministic verification comparing the generated email against the input payload.
    Flags potential fact infringements if they cannot be matched to the input payload.
    """
    combined_email = f"{email_subject}\n{email_body}"
    payload_text = json.dumps(payload).lower()
    
    infringements = []
    
    # 1. Check Numbers
    numbers_found = extract_numbers(combined_email)
    for num in numbers_found:
        clean_num = num.replace("$", "").replace(",", "").lower()
        if clean_num not in payload_text:
            infringements.append({
                "type": "Number",
                "value": num,
                "message": f"Numeric value '{num}' was not found in the input details."
            })
            
    # 2. Check Dates
    dates_found = extract_dates(combined_email)
    for date in dates_found:
        clean_date = date.lower()
        if clean_date not in payload_text:
            infringements.append({
                "type": "Date/Time",
                "value": date,
                "message": f"Date/Time component '{date}' was not found in the input details."
            })
            
    # 3. Check Named Entities (Proper Nouns)
    entities_found = extract_proper_nouns(combined_email)
    for ent in entities_found:
        # Check individual words in this capitalized phrase
        words = ent.split()
        unmatched_words = []
        for w in words:
            if w in COMMON_IGNORES:
                continue
            if w.lower() not in payload_text:
                unmatched_words.append(w)
                
        if unmatched_words:
            infringements.append({
                "type": "Named Entity / Proper Noun",
                "value": ent,
                "message": f"Proper noun / name '{ent}' contains unlisted term(s): {', '.join(unmatched_words)}."
            })
            
    is_valid = len(infringements) == 0
    
    return {
        "is_valid": is_valid,
        "infringements": infringements
    }
