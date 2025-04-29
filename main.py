from flask import Flask, request, jsonify
import requests
import os
import logging
from datetime import datetime, timedelta

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load multiple API keys and Search Engine ID from environment variables
API_KEYS = [
    os.getenv("API_KEY_1"),
    os.getenv("API_KEY_2"),
    os.getenv("API_KEY_3"),
    os.getenv("API_KEY_4")
]
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

# Track API key usage (in-memory, reset daily)
api_key_usage = {key: {"count": 0, "last_reset": datetime.now()} for key in API_KEYS if key}
current_api_key_index = 0
REQUEST_LIMIT = 1000  # Daily limit per API key

# Define websites for different sects
FIRQA_SITES = {
    "barelvi": "site:thefatwa.com",
    "deobandi": "site:banuri.edu.pk",
    "ahlehadith": "site:ahlelhadith.com OR site:forum.mohaddis.com",
}

def reset_usage_if_new_day():
    """Reset API key usage counts if a new day has started."""
    global api_key_usage
    now = datetime.now()
    for key in api_key_usage:
        if now - api_key_usage[key]["last_reset"] >= timedelta(days=1):
            api_key_usage[key]["count"] = 0
            api_key_usage[key]["last_reset"] = now

def get_next_api_key():
    """Get the next available API key with remaining quota."""
    global current_api_key_index
    reset_usage_if_new_day()

    for _ in range(len(API_KEYS)):
        key = API_KEYS[current_api_key_index]
        if not key:
            current_api_key_index = (current_api_key_index + 1) % len(API_KEYS)
            continue
        if api_key_usage[key]["count"] < REQUEST_LIMIT:
            return key
        current_api_key_index = (current_api_key_index + 1) % len(API_KEYS)
    
    return None  # All keys exhausted

def search_google(query, firqa_sites="", start=1):
    """Search Google Custom Search API with pagination support."""
    if not SEARCH_ENGINE_ID:
        return {"error": "Search Engine ID is missing"}, 400
    
    api_key = get_next_api_key()
    if not api_key:
        return {"error": "All API keys have reached their daily limit"}, 429

    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": f"{query} {firqa_sites}" if firqa_sites else query,
        "key": api_key,
        "cx": SEARCH_ENGINE_ID,
        "start": start,
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        api_key_usage[api_key]["count"] += 1  # Increment usage count
        data = response.json()
        return data.get("items", []), 200
    except requests.exceptions.HTTPError as e:
        if e.response.status_code in [403, 429]:  # Quota exceeded or rate limit
            api_key_usage[api_key]["count"] = REQUEST_LIMIT  # Mark as exhausted
            logger.warning(f"API key {api_key} quota exceeded, switching to next key")
            return search_google(query, firqa_sites, start)  # Retry with next key
        logger.error(f"Search failed: {str(e)}")
        return {"error": str(e)}, 500
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
        results["deobandi"] = deobandi_results

        # Step 2: Fetch results from other sects
        combined_sites = f"{FIRQA_SITES['barelvi']} OR {FIRQA_SITES['ahlehadith']}"
        other_results, status = search_google(query, combined_sites)
        if status != 200:
            return jsonify(other_results), status
        results["others"] = other_results

    return jsonify(results), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)