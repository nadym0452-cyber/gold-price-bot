import os
import base64
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = "nadym0452-cyber/gold-price-bot"
DB_FILENAME = "shops.db"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DB_FILENAME}"


def download_db(local_path):
    if not GITHUB_TOKEN:
        return False
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        resp = requests.get(API_URL, headers=headers, timeout=30)
        if resp.status_code == 200:
            content = resp.json()["content"]
            data = base64.b64decode(content)
            with open(local_path, "wb") as f:
                f.write(data)
            return True
    except Exception as e:
        print(f"تعذر تحميل قاعدة البيانات من GitHub: {e}")
    return False


def upload_db(local_path):
    if not GITHUB_TOKEN:
        return False
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        with open(local_path, "rb") as f:
            content = base64.b64encode(f.read()).decode()

        sha = None
        resp = requests.get(API_URL, headers=headers, timeout=30)
        if resp.status_code == 200:
            sha = resp.json().get("sha")

        payload = {"message": "Update shops.db", "content": content}
        if sha:
            payload["sha"] = sha

        put_resp = requests.put(API_URL, headers=headers, json=payload, timeout=30)
        return put_resp.status_code in (200, 201)
    except Exception as e:
        print(f"تعذر رفع قاعدة البيانات لـ GitHub: {e}")
        return False
