# llm_client.py

import os
import requests
import time
import random
from dotenv import load_dotenv

load_dotenv("app.env")

API_KEY = os.getenv("LLM_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

MAX_RETRIES = 1
BASE_DELAY_SECONDS = 2
SYSTEM_PROMPT_PATH = "system_prompt.txt"

def load_system_prompt(file_path: str = SYSTEM_PROMPT_PATH, schema_context: str = "") -> str:
    """
    Loads the system prompt template and dynamically inserts the RAG schema context
    into the {SCHEMA_CONTEXT} placeholder defined in system_prompt.txt.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            template = f.read().strip()
            # CRITICAL: Replace the placeholder with the actual RAG context
            full_prompt = template.replace("{SCHEMA_CONTEXT}", schema_context)
            return full_prompt
    except FileNotFoundError:
        # Return an error string that app.py can catch
        return f"LLM API HTTP Error 400: System prompt file not found at {file_path}"


def generate_sparql_from_question(question: str, schema_context: str) -> str:
    """Sends the question and context to the Gemini API to generate a SPARQL query."""
    if not API_KEY:
        return "LLM API HTTP Error 400: Gemini API key missing. Check app.env."

    # Load system prompt with the integrated schema context
    system_prompt_content = load_system_prompt(schema_context=schema_context)
    
    # If file loading failed, return the error immediately
    if system_prompt_content.startswith("LLM API HTTP Error"):
        return system_prompt_content

    # Simplified user prompt
    user_prompt = f"""Natural Language Question: {question}
SPARQL Query:"""

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt_content}]},
        "contents": [
            {"role": "user", "parts": [{"text": user_prompt}]}
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": API_KEY
    }

    resp = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            break
        except requests.exceptions.HTTPError as e:
            if resp.status_code in (429, 400):
                if attempt == MAX_RETRIES - 1:
                    return f"Gemini API Error {resp.status_code}: {resp.text}"
                delay = BASE_DELAY_SECONDS * (2 ** attempt) + random.uniform(0, 1)
                print(f"[{resp.status_code}] error. Retrying in {delay:.2f}s... (Attempt {attempt+1}/{MAX_RETRIES})")
                time.sleep(delay)
            else:
                return f"LLM API HTTP Error {resp.status_code}: {e}"
        except requests.exceptions.RequestException as e:
            return f"Network error: {e}"

    if resp is None or resp.status_code >= 400:
        return f"Failed to get a successful response from Gemini. Status: {resp.status_code if resp else 'N/A'}"

    data = resp.json()
    try:
        # Extract the generated text (the SPARQL query)
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        if "error" in data:
            return f"Gemini API Error in Response: {data['error']}"
        return f"Gemini response parsing failed: {e}. Raw Data: {data}"