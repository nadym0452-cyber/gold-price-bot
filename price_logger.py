import os
import json
import requests
from datetime import datetime, timezone

HISTORY_FILE = "price_history.json"


def fetch_gold_price_usd():
    resp = requests.get("https://api.gold-api.com/price/XAU", timeout=30)
    resp.raise_for_status()
    return resp.json()["price"]


def fetch_usd_to_egp():
    resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=30)
    resp.raise_for_status()
    return resp.json()["rates"]["EGP"]


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []


def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)


def main():
    gold_usd = fetch_gold_price_usd()
    egp_rate = fetch_usd_to_egp()
    gram24 = (gold_usd * egp_rate) / 31.1035

    history = load_history()
    now = datetime.now(timezone.utc).isoformat()
    history.append({"time": now, "price": round(gram24, 2)})

    cutoff = datetime.now(timezone.utc).timestamp() - (7 * 3600)
    history = [h for h in history if datetime.fromisoformat(h["time"]).timestamp() > cutoff]

    save_history(history)


if __name__ == "__main__":
    main()
