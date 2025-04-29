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

# Filter out None or empty keys and validate
API_KEYS = [key for key in API_KEYS if key and isinstance(key, str) and key.strip()]
if not API_KEYS:
    logger.error("No valid API keys provided. Check environment variables.")
    API_KEYS = []  # Ensure API_KEYS is a list even if empty
if not SEARCH_ENGINE_ID:
    logger.error("Search Engine ID is missing. Check SEARCH_ENGINE_ID environment variable.")

# Track API key usage (in-memory, reset daily)
api_key_usage = {key: {"count": 0, "last_reset": datetime.now()} for key in API_KEYS}
current_api_key_index = 0
REQUEST_LIMIT = 2  # Daily limit per API key for testing (set to 1000 in production)

# Log initial state
logger.info(f"Loaded API keys: {len(API_KEYS)} keys {[key[:8] + '...' for key in API_KEYS]}")
logger.info(f"Search Engine ID: {SEARCH_ENGINE_ID}")
logger.info(f"Initial api_key_usage: {api_key_usage}")

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
            logger.info(f"Reset usage for API key {key[:8]}...: count = 0")

def get_next_api_key():
    """Get the next available API key with remaining quota."""
    global current_api_key_index
    if not API_KEYS:
        logger.error("No API keys available")
        return None

    reset_usage_if_new_day()
    logger.info(f"Current API key index: {current_api_key_index}")
    logger.info(f"Current api_key_usage: {api_key_usage}")

    start_index = current_api_key_index
    for _ in range(len(API_KEYS)):
        key = API_KEYS[current_api_key_index]
        logger.info(f"Checking API key {key[:8]}... (index {current_api_key_index}, count {api_key_usage[key]['count']}/{REQUEST_LIMIT})")
        if api_key_usage[key]["count"] < REQUEST_LIMIT:
            logger.info(f"Selected API key {key[:8]}... with {api_key_usage[key]['count']} requests used")
            return key
        logger.info(f"API key {key[:8]}... has reached limit ({api_key_usage[key]['count']}/{REQUEST_LIMIT})")
        current_api_key_index = (current_api_key_index + 1) % len(API_KEYS)
        if current_api_key_index == start_index:
            logger.error("All API keys have reached their daily limit")
            return None
    
    logger.error("No available API keys after checking all")
    return None

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
        logger.info(f"Making request with API key {api_key[:8]}... for query: {query}")
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        api_key_usage[api_key]["count"] += 1
        logger.info(f"Request successful, incremented count for {api_key[:8]}...: {api_key_usage[api_key]['count']}/{REQUEST_LIMIT}")
        data = response.json()
        return data.get("items", []), 200
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        error_message = e.response.text
        logger.error(f"HTTP error {status_code} with API key {api_key[:8]}...: {error_message}")
        if status_code in [403, 429]:
            api_key_usage[api_key]["count"] = REQUEST_LIMIT
            logger.warning(f"API key {api_key[:8]}... quota exceeded, switching to next key")
            return search_google(query, firqa_sites, start)
        return {"error": f"HTTP error {status_code}: {error_message}"}, status_code
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed with API key {api_key[:8]}...: {str(e)}")
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
        deobandi_results, status = search_google(query, FIRQA_SITES["deobandi"])
        if status != 200:
            return jsonify(deobandi_results), status
        results["deobandi"] = deobandi_results

        combined_sites = f"{FIRQA_SITES['barelvi']} OR {FIRQA_SITES['ahlehadith']}"
        other_results, status = search_google(query, combined_sites)
        if status != 200:
            return jsonify(other_results), status
        results["others"] = other_results

    return jsonify(results), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)