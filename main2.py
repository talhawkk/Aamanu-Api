from flask import Flask, request, jsonify
import requests
import os
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load API key and Search Engine ID from environment variables
API_KEY = os.getenv("API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

# Define websites for different sects
FIRQA_SITES = {
    "barelvi": "site:thefatwa.com",
    "barelvi_fallback": "site:daruliftaahlesunnat.net OR site:daruliftabareilly.com",
    "deobandi": "site:banuri.edu.pk",  
    "deobandi_fallback": "site:darulifta-deoband.com OR site:darulifta-deoband.com/en",  
    "ahlehadith": "site:ahlelhadith.com OR site:forum.mohaddis.com",
}

def search_google(query, firqa_sites="", start=1):
    """Search Google Custom Search API with pagination support."""
    if not API_KEY or not SEARCH_ENGINE_ID:
        return {"error": "API configuration is missing"}, 400
    
    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": f"{query} {firqa_sites}" if firqa_sites else query,
        "key": API_KEY,
        "cx": SEARCH_ENGINE_ID,
        "start": start,  # Pagination starting point
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("items", []), 200
    except requests.exceptions.RequestException as e:
        logger.error(f"Search failed: {str(e)}")
        return {"error": str(e)}, 500

@app.route("/search", methods=["GET"])
def search():
    """Handle search queries with optional sect filter and fallback logic."""
    query = request.args.get("query", "").strip()
    firqa = request.args.get("firqa", "").strip().lower()

    if not query:
        return jsonify({"error": "Query is required"}), 400

    if firqa and firqa not in ["barelvi", "deobandi", "ahlehadith"]:
        return jsonify({"error": "Invalid sect specified"}), 400

    results = {}
    if firqa in ["deobandi", "barelvi", "ahlehadith"]:
        if firqa == "deobandi":
            banuri_results, status = search_google(query, FIRQA_SITES["deobandi"])
            if status != 200:
                return jsonify(banuri_results), status
            results["deobandi"] = banuri_results
            if isinstance(banuri_results, list) and len(banuri_results) < 2:
                fallback_results, fallback_status = search_google(query, FIRQA_SITES["deobandi_fallback"])
                if fallback_status != 200:
                    return jsonify(fallback_results), fallback_status
                if isinstance(fallback_results, list):
                    results["deobandi"] = banuri_results + fallback_results
        elif firqa == "barelvi":
            barelvi_results, status = search_google(query, FIRQA_SITES["barelvi"])
            if status != 200:
                return jsonify(barelvi_results), status
            results["barelvi"] = barelvi_results
            if isinstance(barelvi_results, list) and len(barelvi_results) < 2:
                fallback_results2, fallback_status = search_google(query, FIRQA_SITES["barelvi_fallback"])
                if fallback_status != 200:
                    return jsonify(fallback_results2), fallback_status
                if isinstance(fallback_results2, list):
                    results["barelvi"] = barelvi_results + fallback_results2
        else:  # ahlehadith
            ahlehadith_results, status = search_google(query, FIRQA_SITES["ahlehadith"])
            if status != 200:
                return jsonify(ahlehadith_results), status
            results[firqa] = ahlehadith_results
    else:
        combined_sites = " OR ".join([FIRQA_SITES["barelvi"], FIRQA_SITES["deobandi"], FIRQA_SITES["ahlehadith"]])
        all_results, status = search_google(query, combined_sites)
        if status != 200:
            return jsonify(all_results), status
        results["all"] = all_results
    
    return jsonify(results), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)