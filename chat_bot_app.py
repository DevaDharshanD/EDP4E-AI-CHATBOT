import os
from flask import Flask, request, render_template, jsonify 
from dotenv import load_dotenv

# Import our new caching client wrapper
from llm_client import generate_sparql_from_question
from sparql_guard import validate_sparql 
from fuseki_client import run_sparql_select

load_dotenv("app.env")

# --- Configuration ---
Queries_Dir = r"C:\Users\DDHARSHA\Documents\APP\Queries" # Ensure this path exists or is correct
LOGGING_ENABLED = os.getenv("LOGGING_ENABLED", "false").lower() == "true"
FUSEKI_ENDPOINT = os.getenv("FUSEKI_ENDPOINT")
SCHEMA_PATH = os.environ.get("SCHEMA_PATH", "Schema.ttl")

# --- Pre-defined Industry Questions ---
IndustryQuestions = [
    "List vehicles battery compliance and carboon footprint Data",
    "List_Vehicles_whose_batteries_likely_suffering_from_harmful_charge_and_discharge_events",
    "List_Vehicles_with_HighEnergyBatteriesWithMinimalIdleTempAnd_Chem_As_NMC",
    "RatedCapacityVsNominalCapacityMismatchOverFivePercent",
    "Vehicle's_Battery_manufacturing_date_earlier_than_delivery_Date",
    "Vehicles_Battery_voltage_consistency_check",
    "Vehicles_Battery_with_high_usable_energy_and_low_Efficiency",
    "Vehicles_Battery_with_Solid_state_chemistry_and_mass_greater_than_600",
    "Vehicles_With_Solid_State_Battery_and_warrant_greater_Than_2"
] 

app = Flask(__name__)

# Note: We no longer strictly need 'SchemaRAG' for the LLM path 
# because the full schema is now cached in 'llm_client.py'.

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/query", methods=["POST"])
def query():
    payload = request.get_json(force=True, silent=True)
    if payload is None:
        return jsonify({"error": "Invalid JSON"}), 400

    question = (payload.get("question") or "").strip()
    sparql = ""

    # 1. Exact Match Strategy (Pre-canned queries)
    if question in IndustryQuestions:
        if LOGGING_ENABLED: print(f"Strategy: Pre-defined Industry Question")
        file_path = os.path.join(Queries_Dir, f"{question}.sparql")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                sparql = f.read().strip()
        except FileNotFoundError:
            return jsonify({"error": f"Pre-defined SPARQL file missing for: {question}"}), 500

    # 2. Generative AI Strategy (Context Caching)
    else:
        if LOGGING_ENABLED: print(f"Strategy: Gemini Context Cache")
        
        # We pass empty string for context because the client handles caching internally
        sparql = generate_sparql_from_question(question, "")

        # Error Handling for LLM responses
        if "Error" in sparql or sparql.startswith("Failed"):
            return jsonify({"error": sparql, "sparql": None}), 503

    # 3. Validation
    try:
        validate_sparql(sparql)
    except ValueError as ve:
        return jsonify({"error": f"SPARQL Validation Error: {ve}", "sparql": sparql}), 400

    # 4. Execution (Fuseki)
    try:
        results = run_sparql_select(FUSEKI_ENDPOINT, sparql)
    except RuntimeError as re:
        return jsonify({"error": str(re), "sparql": sparql}), 500

    if LOGGING_ENABLED:
        print(f"--- Generated Query ---\n{sparql}\n-----------------------")

    return jsonify({"sparql": sparql, "results": results})

if __name__ == "__main__":
    if not FUSEKI_ENDPOINT:
        print("WARNING: FUSEKI_ENDPOINT not set in app.env")
    print("Starting JLR Supply Chain Assistant (Caching Enabled)...")
    app.run(host="127.0.0.1", port=8000, debug=True)