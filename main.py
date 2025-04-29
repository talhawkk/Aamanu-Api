from flask import Flask, request, jsonify
import requests
import os
import logging
from datetime import datetime, timedelta

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Load API keys and Search Engine ID
API_KEYS = [
    os.getenv("API_KEY_1"),
    os.getenv("API_KEY_2"),
    os.getenv("API_KEY_3"),
    os.getenv("API_KEY_4")
]
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

# Validate keys
API_KEYS = [key for key in API_KEYS if key and isinstance(key, str) and key.strip()]
if not API_KEYS:
    logger.error("No valid API keys provided.")
if not SEARCH_ENGINE_ID:
    logger.error("Search Engine ID is missing.")

# Track usage
api_key_usage = {key: {"count": 0, "last_reset": datetime.now()} for key in API_KEYS}
current_api_key_index = 0
REQUEST_LIMIT = 1000

# Firqa site mapping
FIRQA_SITES = {
    "barelvi": "site:thefatwa.com",
    "deobandi": "site:banuri.edu.pk",
    "ahlehadith": "site:ahlelhadith.com"
}

def reset_usage_if_new_day():
    now = datetime.now()
    for key in api_key_usage:
        if now - api_key_usage[key]["last_reset"] >= timedelta(days=1):
            api_key_usage[key]["count"] = 0
            api_key_usage[key]["last_reset"] = now

def get_next_api_key():
    global current_api_key_index
    reset_usage_if_new_day()
    start_index = current_api_key_index
    for _ in range(len(API_KEYS)):
        key = API_KEYS[current_api_key_index]
        if api_key_usage[key]["count"] < REQUEST_LIMIT:
            return key
        current_api_key_index = (current_api_key_index + 1) % len(API_KEYS)
        if current_api_key_index == start_index:
            return None
    return None

def search_google(query, firqa_sites, start=1):
    if not SEARCH_ENGINE_ID:
        return {"error": "Search Engine ID is missing"}, 400

    api_key = get_next_api_key()
    if not api_key:
        return {"error": "All API keys have reached their daily limit"}, 429

    params = {
        "q": f"{query} {firqa_sites}",
        "key": api_key,
        "cx": SEARCH_ENGINE_ID,
        "start": start,
    }

    try:
        response = requests.get("https://www.googleapis.com/customsearch/v1", params=params)
        response.raise_for_status()
        api_key_usage[api_key]["count"] += 1
        data = response.json()
        return data.get("items", []), 200
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        if status_code in [403, 429]:
            api_key_usage[api_key]["count"] = REQUEST_LIMIT
            return search_google(query, firqa_sites, start)
        return {"error": f"HTTP error {status_code}: {e.response.text}"}, status_code
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}, 500

@app.route("/search", methods=["GET"])
def search():
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
        for sect, site in FIRQA_SITES.items():
            firqa_results, status = search_google(query, site)
            if status == 200:
                results[sect] = firqa_results

    return jsonify(results), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
