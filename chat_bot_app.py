# app.py

import os
# CHANGE: Import render_template (not render_template_string)
from flask import Flask, request, render_template, jsonify 
# Assuming supporting files are in the same directory
from llm_client import generate_sparql_from_question
from sparql_guard import validate_sparql 
from fuseki_client import run_sparql_select
from dotenv import load_dotenv
from RAG_Schema import SchemaRAG
# Note: Removed the redundant 'import json' and diagnostic print statements

load_dotenv("app.env")

# --- industry Questions ---
IndustryQuestions=["List vehicle battery compliance and carboon footprint Data",
                   "List_Vehicles_whose_batteries_likely_suffering_from_harmful_charge_and_discharge_events",
                   "List_Vehicles_with_HighEnergyBatteriesWithMinimalIdleTempAnd_Chem_As_NMC",
                   "RatedCapacityVsNominalCapacityMismatchOverFivePercent",
                   "Vehicle's_Battery_manufacturing_date_earlier_than_delivery_Date",
                   "Vehicles_Battery_voltage_consistency_check",
                   "Vehicles_Battery_with_high_usable_energy_and_low_Efficiency",
                   "Vehicles_Battery_with_Solid_state_chemistry_and_mass_greater_than_600",
                   "Vehicles_With_Solid_State_Battery_and_warrant_greater_Than_2"
] 
Queries_Dir=r"C:\Users\DDHARSHA\Documents\APP\Queries"


# --- Environment Configuration ---
try:
    SCHEMA_PATH = os.environ["SCHEMA_PATH"]
    FUSEKI_ENDPOINT = os.environ["FUSEKI_ENDPOINT"]
except KeyError as e:
    raise RuntimeError(f"Missing environment variable: {e}. Check app.env.")

# Controls print output for debugging
LOGGING_ENABLED = os.getenv("LOGGING_ENABLED", "false").lower() == "true"

# --- Initialization ---
app = Flask(__name__)
# Initialize RAG system with the schema file
schema_rag = SchemaRAG(SCHEMA_PATH)

# --- Flask Routes ---

@app.route("/", methods=["GET"])
def index():
    """Renders the HTML interface from the external template file (templates/index.html)."""
    # CHANGE: Uses render_template to look in the 'templates' folder
    return render_template("index.html")

@app.route("/query", methods=["POST"])
def query():
    """Handles the query generation and execution pipeline."""
    payload = request.get_json(force=True, silent=True)
    
    if payload is None:
        return jsonify({"error": "Invalid JSON request body. Server received empty or corrupt data."}), 400

    question = (payload.get("question") or "").strip()
    if question in IndustryQuestions:
        print("IndustryQuestions")
        # Build file path: queries/<question>.sparql
        file_path = os.path.join(Queries_Dir, f"{question}.sparql")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                sparql = f.read().strip()
        except FileNotFoundError:
            raise ValueError(f"SPARQL file not found for question: {question}")

    else:
        print("LLM Approach")
        schema_context = schema_rag.retrieve(question, k=5) 
        sparql = generate_sparql_from_question(question, schema_context)

        # --- Error Mapping and Handling (LLM/API related) ---
        if "Rate limit exceeded" in sparql or "RESOURCE_EXHAUSTED" in sparql:
            return jsonify({"error": "Gemini quota exceeded (429). Please wait for reset.", "sparql": None}), 429
        if sparql.startswith("LLM API HTTP Error 400"):
            return jsonify({"error": "Bad request to Gemini (400). Prompt too large or invalid key/path.", "sparql": None}), 400
        if sparql.startswith(("LLM API HTTP Error", "Network error", "Failed to get")):
            return jsonify({"error": sparql, "sparql": None}), 503

    # --- Validation ---
    try:
        validate_sparql(sparql)
    except Exception as e:
        return jsonify({"error": f"SPARQL validation failed: {e}", "sparql": sparql}), 400

    # --- Execution ---
    try:
        results = run_sparql_select(FUSEKI_ENDPOINT, sparql)
    except Exception as e:
        return jsonify({"error": f"Fuseki query failed: {e}", "sparql": sparql}), 500

    if LOGGING_ENABLED:
        print("Question:", question)
        print("SPARQL:", sparql)

    return jsonify({"sparql": sparql, "results": results})

if __name__ == "__main__":
    print("Starting Knowledge Graph RAG Assistant on http://127.0.0.1:8000/")
    app.run(host="127.0.0.1", port=8000, debug=True)