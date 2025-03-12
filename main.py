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
    "deobandi": "site:banuri.edu.pk",  
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
    """Handle search queries with optional sect filter."""
    query = request.args.get("query", "").strip()
    firqa = request.args.get("firqa", "").strip().lower()

    if not query:
        return jsonify({"error": "Query is required"}), 400

    if firqa and firqa not in FIRQA_SITES:
        return jsonify({"error": "Invalid sect specified"}), 400

    results = {}
    
    if firqa:
        firqa_results, status = search_google(query, FIRQA_SITES[firqa])
        if status != 200:
            return jsonify(firqa_results), status
        results[firqa] = firqa_results
    else:
        # Step 1: Get results from Banuri (Deobandi) first
        deobandi_results, status = search_google(query, FIRQA_SITES["deobandi"])
        if status != 200:
            return jsonify(deobandi_results), status
        results["deobandi"] = deobandi_results  # First priority

        # Step 2: Fetch results from other sects
        combined_sites = f"{FIRQA_SITES['barelvi']} OR {FIRQA_SITES['ahlehadith']}"
        other_results, status = search_google(query, combined_sites)
        if status != 200:
            return jsonify(other_results), status
        results["others"] = other_results  # Other sects' results

    return jsonify(results), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
