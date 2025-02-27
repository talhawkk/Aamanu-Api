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
    "barelvi": "site:thefatwa.com OR site:daruliftaahlesunnat.net OR site:daruliftabareilly.com",
    "deobandi": "site:banuri.edu.pk",  # Primary site for Deobandi
    "deobandi_fallback": "site:darulifta-deoband.com OR site:darulifta-deoband.com/en",  # Fallback sites
    "ahlehadith": "site:ahlelhadith.com OR site:forum.mohaddis.com",
}

def search_google(query, firqa_sites=""):
    """Search Google Custom Search API."""
    if not API_KEY or not SEARCH_ENGINE_ID:
        return {"error": "API configuration is missing"}
    
    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": f"{query} {firqa_sites}" if firqa_sites else query,
        "key": API_KEY,
        "cx": SEARCH_ENGINE_ID,
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json().get("items", [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Search failed: {str(e)}")
        return {"error": str(e)}

@app.route("/search", methods=["GET"])
def search():
    """Handle search queries with optional sect filter."""
    query = request.args.get("query", "").strip()
    firqa = request.args.get("firqa", "").strip().lower()

    if not query:
        return jsonify({"error": "Query is required"}), 400

    if firqa and firqa not in ["barelvi", "deobandi", "ahlehadith"]:
        return jsonify({"error": "Invalid sect specified"}), 400

    results = {}
    if firqa == "deobandi":
        # Step 1: Pehle Banuri se search karo
        banuri_results = search_google(query, FIRQA_SITES["deobandi"])
        results["deobandi"] = banuri_results
        
        # Step 2: Agar Banuri se 2 se kam results milen, to fallback sites se search
        if isinstance(banuri_results, list) and len(banuri_results) < 2:
            fallback_results = search_google(query, FIRQA_SITES["deobandi_fallback"])
            if isinstance(fallback_results, list):
                results["deobandi"] = banuri_results + fallback_results  # All available results
    elif firqa in FIRQA_SITES:
        results[firqa] = search_google(query, FIRQA_SITES[firqa])
    else:
        combined_sites = " OR ".join([FIRQA_SITES["barelvi"], FIRQA_SITES["deobandi"], FIRQA_SITES["ahlehadith"]])
        results["all"] = search_google(query, combined_sites)
    
    return jsonify(results), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)