import os
import re
import urllib.parse
import pandas as pd
from flask import Flask, request, render_template, jsonify 
from dotenv import load_dotenv
from rapidfuzz import fuzz

# Import custom modules
from llm_client import generate_sparql_from_question
from sparql_guard import validate_sparql 
from fuseki_client import run_sparql_select

load_dotenv("app.env")

# --- Configuration ---
Queries_Dir = r"C:\Users\DDHARSHA\Documents\APP\Queries" 
EXCEL_FILE_PATH = r"C:\Users\DDHARSHA\Documents\APP\input.xlsx" 

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

# --- Load Excel Data for QR Mapping ---
def load_excel_data():
    if not os.path.exists(EXCEL_FILE_PATH):
        print(f"CRITICAL: Excel file not found at {EXCEL_FILE_PATH}")
        return {}
    try:
        df = pd.read_excel(EXCEL_FILE_PATH, sheet_name='MFG')
        df.columns = df.columns.str.strip()
        return dict(zip(df['BatteryID'].astype(str).str.upper(), df['Product Information']))
    except Exception as e:
        print(f"Error loading Excel MFG sheet: {e}")
        return {}

BATTERY_MAP = load_excel_data()

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/query", methods=["POST"])
def query():
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"error": "Invalid JSON"}), 400

    question = (payload.get("question") or "").strip()
    sparql = None

    # =========================================================================
    # Strategy 1: QR Code / Product Info Lookup (Excel Path)
    # =========================================================================
    battery_match = re.search(r"(BATTERY-\d+)", question, re.IGNORECASE)
    
    # Fuzzy check for "product information" or "prod info"
    is_prod_request = (
        fuzz.partial_ratio(question, "product information") > 80 or 
        fuzz.partial_ratio(question, "prod info") > 80 or
        fuzz.partial_ratio(question, "product info") > 80 )

    if battery_match and is_prod_request:
        bid = battery_match.group(1).upper()
        if bid in BATTERY_MAP:
            target_url = BATTERY_MAP[bid]
            encoded_url = urllib.parse.quote(target_url)
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?data={encoded_url}&size=150x150"
            
            return jsonify({
                "type": "qr",
                "message": f"Scan this QR Code for Product Info",
                "qr_url": qr_url,
                "target_url": target_url,
                "sparql": "N/A (Direct Excel Lookup)",
                "results": {"status": "QR Generated", "source": "Database"}
            })
        else:
            return jsonify({"error": f"Battery ID {bid} is invalid!"}), 404

    # =========================================================================
    # Strategy 2: Pre-defined Industry Questions (Exact Match)
    # =========================================================================
    if question in IndustryQuestions:
        if LOGGING_ENABLED: print(f"Strategy: Pre-defined Industry Question")
        file_path = os.path.join(Queries_Dir, f"{question}.sparql")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                sparql = f.read().strip()
        except FileNotFoundError:
            return jsonify({"error": f"Pre-defined SPARQL file missing", "sparql": None}), 500

    # =========================================================================
    # Strategy 3: Generative AI Strategy (Context Caching)
    # =========================================================================
    else:
        if LOGGING_ENABLED: print(f"Strategy: Gemini Context Cache")
        sparql = generate_sparql_from_question(question, "")
        
        if not sparql or "Error" in sparql or sparql.startswith("Failed"):
            return jsonify({"error": sparql or "AI failed to generate query", "sparql": None}), 503

    # =========================================================================
    # 3. Validation & Execution
    # =========================================================================
    try:
        validate_sparql(sparql)
        results = run_sparql_select(FUSEKI_ENDPOINT, sparql)
        
        if LOGGING_ENABLED:
            print(f"--- Generated Query ---\n{sparql}\n-----------------------")
            
        return jsonify({"type": "sparql", "sparql": sparql, "results": results})

    except Exception as e:
        return jsonify({"error": str(e), "sparql": sparql}), 500

if __name__ == "__main__":
    if not FUSEKI_ENDPOINT:
        print("WARNING: FUSEKI_ENDPOINT not set in app.env")
    
    print(f"✅ Assistant Ready. Loaded {len(BATTERY_MAP)} records from Excel.")
    print("Starting JLR Supply Chain Assistant (Caching + Excel QR Enabled)...")
    app.run(host="127.0.0.1", port=8000, debug=True)