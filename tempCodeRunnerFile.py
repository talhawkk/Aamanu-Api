from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Load API key and Search Engine ID from environment variables
API_KEY = os.getenv("API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

# Define websites for different sects (FIRQA_SITES)
FIRQA_SITES = {
    "barelvi": "site:thefatwa.com OR site:daruliftaahlesunnat.net OR site:daruliftabareilly.com",
    "deobandi": "site:darulifta-deoband.com OR site:banuri.edu.pk OR site:darulifta-deoband.com/en",
    "ahlehadith": "site:ahlelhadith.com OR site:forum.mohaddis.com",
}

def search_google(query, firqa_sites=""):
    """Search Google Custom Search API."""
    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": f"{query} {firqa_sites}" if firqa_sites else query,
        "key": API_KEY,
        "cx": SEARCH_ENGINE_ID,
        "num": 6,
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json().get("items", [])
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

@app.route("/search", methods=["GET"])
def search():
    """Handle search queries with optional sect filter."""
    query = request.args.get("query", "").strip()
    firqa = request.args.get("firqa", "").strip().lower()

    if not query:
        return jsonify({"error": "Query is required"}), 400

    results = {}
    if firqa and firqa in FIRQA_SITES:
        results[firqa] = search_google(query, FIRQA_SITES[firqa])
    else:
        combined_sites = " OR ".join(FIRQA_SITES.values())
        results["all"] = search_google(query, combined_sites)
    
    return jsonify(results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Railway dynamically assigns a port
    app.run(host="0.0.0.0", port=port, debug=True)
