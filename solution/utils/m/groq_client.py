import os
import time
import logging
from typing import Dict, Any, Optional
from groq import Groq
from groq import (
    GroqError,
    APIError,
    APIStatusError,
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_groq_client(api_key: Optional[str] = None) -> Groq:
    """
    Get a Groq client instance. Proactively checks environment variables
    if an explicit key is not provided.
    """
    key = api_key or os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("Groq API Key is not set. Please provide it in the sidebar or check your environment configuration.")
    return Groq(api_key=key)

def truncate_text(text: str, max_chars: int = 30000) -> str:
    """
    Truncate text to prevent exceeding context window limits.
    Roughly, 30000 characters is about 6000-8000 tokens.
    """
    if len(text) <= max_chars:
        return text
    logger.warning(f"Text truncated from {len(text)} to {max_chars} characters.")
    return text[:max_chars] + "\n\n[... TEXT TRUNCATED FOR CONTEXT LIMITS ...]"

def call_groq_with_retry(
    prompt: str,
    system_prompt: str = "",
    model: str = "llama-3.3-70b-versatile",
    api_key: Optional[str] = None,
    json_mode: bool = False,
    temperature: float = 0.7,
    max_retries: int = 5,
    backoff_factor: float = 2.0
) -> str:
    """
    Calls the Groq API with retries and exponential backoff.
    Handles HTTP 429 (Rate Limits) and 5xx errors.
    """
    client = get_groq_client(api_key)
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    retry_delay = 1.0
    for attempt in range(max_retries):
        try:
            chat_completion = client.chat.completions.create(**kwargs)
            res = chat_completion.choices[0].message.content
            if res is None:
                raise ValueError("Groq returned an empty message content response.")
            return res
        except AuthenticationError as e:
            logger.error(f"Groq Authentication Error: {e}")
            raise ValueError("Invalid Groq API key. Please check your key in the System Control Panel and try again.") from e
        except RateLimitError as e:
            if attempt == max_retries - 1:
                logger.error("Rate limit hit. Max retries reached.")
                raise e
            wait_time = retry_delay * (backoff_factor ** attempt)
            logger.warning(f"Rate limit hit. Retrying in {wait_time:.2f} seconds... Error: {e}")
            time.sleep(wait_time)
        except APITimeoutError as e:
            if attempt == max_retries - 1:
                logger.error("API Timeout. Max retries reached.")
                raise e
            wait_time = retry_delay * (backoff_factor ** attempt)
            logger.warning(f"Timeout occurred. Retrying in {wait_time:.2f} seconds... Error: {e}")
            time.sleep(wait_time)
        except APIConnectionError as e:
            if attempt == max_retries - 1:
                logger.error("API Connection Error. Max retries reached.")
                raise e
            wait_time = retry_delay * (backoff_factor ** attempt)
            logger.warning(f"Connection error. Retrying in {wait_time:.2f} seconds... Error: {e}")
            time.sleep(wait_time)
        except APIStatusError as e:
            if e.status_code == 404:
                logger.error(f"Groq API Error 404 (Model Not Found): {e}")
                raise ValueError(f"The selected model '{model}' is not found or is no longer active on Groq.") from e
            if e.status_code >= 500 and attempt < max_retries - 1:
                wait_time = retry_delay * (backoff_factor ** attempt)
                logger.warning(f"Groq API Error {e.status_code}. Retrying in {wait_time:.2f} seconds... Error: {e}")
                time.sleep(wait_time)
                continue
            raise e
        except Exception as e:
            logger.error(f"Unexpected error calling Groq API: {e}")
            raise e
            
    raise RuntimeError("Failed to call Groq API after maximum retries.")
