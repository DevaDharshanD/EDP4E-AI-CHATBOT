import os
import requests
import time
import json
from dotenv import load_dotenv

load_dotenv("app.env")

API_KEY = os.getenv("LLM_API_KEY")

# Caching requires specific versioned models (e.g., -001), not generic aliases
MODEL_NAME = "models/gemini-1.5-flash-001" 
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

class GeminiCacheClient:
    def __init__(self, system_prompt_path="system_prompt.txt", schema_path="Schema.ttl"):
        self.system_prompt_path = system_prompt_path
        self.schema_path = schema_path
        self.cache_name = None
        self.cache_expiration = 0
        
        # Load file contents immediately
        self.full_system_instruction = self._build_system_instruction()

    def _build_system_instruction(self) -> str:
        """Reads files and merges Schema into the System Prompt."""
        try:
            with open(self.system_prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            
            # We use the FULL schema for caching, not just snippets
            with open(self.schema_path, "r", encoding="utf-8") as f:
                schema_content = f.read()

            # Merge
            return prompt_template.replace("{SCHEMA_CONTEXT}", schema_content)
        except FileNotFoundError as e:
            print(f"CRITICAL ERROR: {e}")
            return ""

    def _create_cache(self):
        """Creates a new cache on Google servers and returns the resource name."""
        url = f"{BASE_URL}/cachedContents?key={API_KEY}"
        
        payload = {
            "model": MODEL_NAME,
            "displayName": "JLR_SupplyChain_Context",
            "systemInstruction": {
                "parts": [{"text": self.full_system_instruction}]
            },
            # Cache for 1 hour (3600s). You can increase this if needed.
            "ttl": "3600s"
        }

        print("Creating new Gemini Context Cache...")
        try:
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            self.cache_name = data["name"]
            # Set local expiry time (subtract 60s for safety buffer)
            self.cache_expiration = time.time() + 3600 - 60
            print(f"Cache Active: {self.cache_name} (Expires in 1 hr)")
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to create cache: {e}")
            self.cache_name = None

    def generate_sparql(self, question: str) -> str:
        """Generates SPARQL using the active cache ID."""
        if not API_KEY:
            return "Error: LLM_API_KEY is missing."

        # 1. Check if cache exists and is valid
        if not self.cache_name or time.time() > self.cache_expiration:
            self._create_cache()
            if not self.cache_name:
                return "Error: Could not create context cache. Check logs."

        # 2. Prepare Request
        # Note: We do NOT send system_instruction here (it's in the cache)
        url = f"{BASE_URL}/{MODEL_NAME}:generateContent?key={API_KEY}"
        
        user_prompt = f"Natural Language Question: {question}\nSPARQL Query:"
        
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": user_prompt}]}
            ],
            "cachedContent": self.cache_name
        }

        # 3. Execute
        try:
            resp = requests.post(url, json=payload, timeout=30)
            
            # Handle 404 (Cache Not Found) - It might have been deleted remotely
            if resp.status_code == 404:
                print("Cache not found (404). Recreating...")
                self._create_cache()
                # Update payload with new cache name and retry once
                payload["cachedContent"] = self.cache_name
                resp = requests.post(url, json=payload, timeout=30)

            resp.raise_for_status()
            data = resp.json()
            
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            
        except Exception as e:
            return f"Gemini API Error: {str(e)}"

# Singleton Instance
# We instantiate this once so the cache ID persists across Flask requests
llm_client_instance = GeminiCacheClient()

def generate_sparql_from_question(question: str, schema_context_unused: str = "") -> str:
    """Wrapper function to maintain compatibility with app calls."""
    # Note: schema_context_unused is ignored because we cached the FULL schema.
    return llm_client_instance.generate_sparql(question)