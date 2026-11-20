"""Top N z Hacker News trafia do listy jako zwykłe artykuły
(dalej robi je worker: pobranie strony + streszczenie przez Claude).
Odpalane z zewnątrz (cron) przez POST /hn."""
import json
import os
import threading
import urllib.request

import db
import worker

API = "https://hacker-news.firebaseio.com/v0"
TOP_N = int(os.environ.get("WTICZKA_HN_COUNT", "20"))
TIMEOUT = 20

_lock = threading.Lock()


def _get_json(path):
    with urllib.request.urlopen(f"{API}/{path}", timeout=TIMEOUT) as res:
        return json.load(res)


def fetch_top():
    """Dodaje top N historii z HN, których jeszcze nie ma w bazie. Zwraca liczbę dodanych."""
    with _lock:
        added = 0
        for story_id in _get_json("topstories.json")[:TOP_N]:
            try:
                item = _get_json(f"item/{story_id}.json") or {}
            except Exception as err:
                print(f"HN: nie pobrałem #{story_id}: {err}")
                continue
            if item.get("type") != "story" or item.get("dead") or item.get("deleted"):
                continue
            # Ask HN / Show HN bez linku: czytamy wątek na HN
            url = item.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
            if db.url_exists(url):
                continue
            article_id = db.add(url, item.get("title", ""), "")
            worker.enqueue(article_id)
            added += 1
        print(f"HN: dodano {added} nowych artykułów")
        return added

