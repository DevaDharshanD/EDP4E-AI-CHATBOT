# llm_client.py

import os
import requests
import time
import json
from dotenv import load_dotenv

load_dotenv("app.env")

API_KEY = os.getenv("LLM_API_KEY")

# Primary Model for Caching (Using 2.0 Flash as it supports createCachedContent)
CACHE_MODEL_NAME = "models/gemini-2.0-flash-lite-preview-02-05"

# Fallback Model (Standard endpoint)
STANDARD_MODEL_NAME = "models/gemini-2.5-flash-lite"

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
            
            with open(self.schema_path, "r", encoding="utf-8") as f:
                schema_content = f.read()

            return prompt_template.replace("{SCHEMA_CONTEXT}", schema_content)
        except FileNotFoundError as e:
            print(f"CRITICAL FILE ERROR: {e}")
            return ""

    def _create_cache(self):
        """Attempts to create a cache. Returns True if successful, False otherwise."""
        url = f"{BASE_URL}/cachedContents?key={API_KEY}"
        
        payload = {
            "model": CACHE_MODEL_NAME,
            "displayName": "EDP4E",
            "systemInstruction": {
                "parts": [{"text": self.full_system_instruction}]
            },
            "ttl": "3600s"
        }

        print("DEBUG: Attempting to create Gemini Context Cache...")
        try:
            resp = requests.post(url, json=payload, timeout=30)
            
            if resp.status_code != 200:
                print(f"WARNING: Cache creation failed [{resp.status_code}].")
                print(f"Server Response: {resp.text}")
                return False

            data = resp.json()
            self.cache_name = data["name"]
            self.cache_expiration = time.time() + 3600 - 60
            print(f"SUCCESS: Cache Active: {self.cache_name} (Expires in 1 hr)")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"WARNING: Network error creating cache: {e}")
            return False

    def generate_sparql(self, question: str) -> str:
        """Generates SPARQL using Cache if available, otherwise falls back to standard."""
        if not API_KEY:
            return "Error: LLM_API_KEY is missing in app.env"

        # 1. Try to ensure cache exists
        use_cache = False
        if self.cache_name and time.time() < self.cache_expiration:
            use_cache = True
        else:
            # Try to create it
            if self._create_cache():
                use_cache = True
            else:
                print("DEBUG: Proceeding with STANDARD (Non-Cached) request.")

        # 2. Prepare Request based on mode
        if use_cache:
            # CACHED MODE
            # {BASE_URL} is https://generativelanguage.googleapis.com/v1beta
            # CACHE_MODEL_NAME already has "models/" prefix
            url = f"{BASE_URL}/{CACHE_MODEL_NAME}:generateContent?key={API_KEY}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": f"Natural Language Question: {question}\nSPARQL Query:"}]}],
                "cachedContent": self.cache_name
            }
        else:
            # FALLBACK / STANDARD MODE
            # Use the variable directly because it now contains "models/"
            url = f"{BASE_URL}/{STANDARD_MODEL_NAME}:generateContent?key={API_KEY}"
            payload = {
                "system_instruction": {"parts": [{"text": self.full_system_instruction}]},
                "contents": [{"role": "user", "parts": [{"text": f"Natural Language Question: {question}\nSPARQL Query:"}]}]
            }

        # 3. Execute
        try:
            resp = requests.post(url, json=payload, timeout=30)
            
            # If Cache was used but not found (404), clear it and retry standard
            if resp.status_code == 404 and use_cache:
                print("DEBUG: Cache 404 (Expired/Deleted). Retrying with standard request...")
                self.cache_name = None
                return self.generate_sparql(question)

            if resp.status_code != 200:
                return f"Gemini API Error {resp.status_code}: {resp.text}"

            data = resp.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except KeyError:
                return f"Error parsing Gemini response: {data}"
            
        except Exception as e:
            return f"Gemini API Exception: {str(e)}"

# Singleton Instance
llm_client_instance = GeminiCacheClient()

def generate_sparql_from_question(question: str, schema_context_unused: str = "") -> str:
    return llm_client_instance.generate_sparql(question)