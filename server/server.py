"""Serwer: odbiera strony z wtyczki (POST /page), zapisuje je w SQLite,
w tle odpala Claude, a pod http://HOST:PORT pokazuje listę do czytania."""
import json
import os
import re
import shutil
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import db
import fetch
import hn
import templates
import worker

HOST = os.environ.get("WTICZKA_HOST", "10.10.10.10")
PORT = int(os.environ.get("WTICZKA_PORT", "8000"))
ALLOWED_ORIGINS = {f"http://{HOST}:{PORT}", f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"}

# Treść od Claude pochodzi z niezaufanych stron, więc żadnych skryptów w przeglądarce.
CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
    "base-uri 'none'; frame-ancestors 'none'"
)

ARTICLE_ACTION = re.compile(r"^/article/(\d+)/(status|retry|delete)$")
ARTICLE_VIEW = re.compile(r"^/article/(\d+)$")
URL_IN_TEXT = re.compile(r"https?://\S+")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            status = parse_qs(url.query).get("status", ["to_read"])[0]
            if status not in db.STATUSES:
                status = "to_read"
            page = templates.list_page(status, db.list_by_status(status), db.counts())
            return self._html(page)

        if m := ARTICLE_VIEW.match(url.path):
            article = db.get(int(m[1]))
            if article is None:
                return self._html(templates.not_found_page(), 404)
            return self._html(templates.article_page(article))

        self._html(templates.not_found_page(), 404)

    def do_POST(self):
        if not self._origin_ok():
            return self._send(403, "text/plain", b"Forbidden")

        path = urlparse(self.path).path
        if path == "/page":
            return self._receive_page()
        if path == "/add":
            return self._add_url()
        if path == "/hn":
            return self._fetch_hn()

        if m := ARTICLE_ACTION.match(path):
            article_id, action = int(m[1]), m[2]
            article = db.get(article_id)
            if article is None:
                return self._html(templates.not_found_page(), 404)

            if action == "status":
                status = self._form().get("status", [""])[0]
                if status in db.STATUSES:
                    db.set_status(article_id, status)
                return self._redirect("/" if status == "read" else f"/article/{article_id}")
            if action == "retry":
                db.set_pending(article_id)
                worker.enqueue(article_id)
                return self._redirect(f"/article/{article_id}")
            if action == "delete":
                db.delete(article_id)
                return self._redirect(f"/?status={article['status']}")

        self._send(404, "text/plain", b"Not found")

    def _receive_page(self):
        data = json.loads(self._body())
        article_id = db.add(data.get("url", ""), data.get("title", ""), data.get("text", ""))
        print(f"Zapisano #{article_id}: {data.get('url')} (Claude pracuje w tle...)")
        worker.enqueue(article_id)
        self._send(200, "application/json", json.dumps({"ok": True, "id": article_id}).encode())

    def _add_url(self):
        """Ręczne dodanie linku: formularz (url=...) albo JSON {"url": "..."}.
        Z udostępniania na telefonie przychodzi często "Tytuł https://...", więc wyciągamy sam URL."""
        is_json = self.headers.get_content_type() == "application/json"
        body = self._body()
        try:
            raw = json.loads(body).get("url", "") if is_json else parse_qs(body.decode()).get("url", [""])[0]
            found = URL_IN_TEXT.search(raw or "")
            if not found:
                raise ValueError("Podaj adres zaczynający się od http:// lub https://")
            url = found[0]
            fetch.check_url(url)
        except (ValueError, AttributeError) as err:
            if is_json:
                return self._send(400, "application/json", json.dumps({"ok": False, "error": str(err)}).encode())
            return self._html(templates.error_page(str(err)), 400)

        article_id = db.add(url, "", "")
        print(f"Dodano ręcznie #{article_id}: {url}")
        worker.enqueue(article_id)
        if is_json:
            return self._send(200, "application/json", json.dumps({"ok": True, "id": article_id}).encode())
        self._redirect(f"/article/{article_id}")

    def _fetch_hn(self):
        """Cron (curl -X POST, bez body) dostaje JSON, przycisk w UI (formularz) wraca na listę."""
        from_form = self.headers.get_content_type() == "application/x-www-form-urlencoded"
        self._body()
        try:
            added = hn.fetch_top()
        except Exception as err:
            if from_form:
                return self._html(templates.error_page(f"Nie udało się pobrać z HN: {err}"), 502)
            return self._send(502, "application/json", json.dumps({"ok": False, "error": str(err)}).encode())
        if from_form:
            return self._redirect("/")
        self._send(200, "application/json", json.dumps({"ok": True, "added": added}).encode())

    def _origin_ok(self):
        origin = self.headers.get("Origin")
        return origin is None or origin.startswith("moz-extension://") or origin in ALLOWED_ORIGINS

    def _body(self):
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def _form(self):
        return parse_qs(self._body().decode())

    def _html(self, page, code=200):
        self._send(code, "text/html; charset=utf-8", page.encode())

    def _redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def _send(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Security-Policy", CSP)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # bez logu każdego requestu


if __name__ == "__main__":
    if not shutil.which("claude"):
        sys.exit("Brak polecenia `claude` w PATH.")
    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        print("UWAGA: brak CLAUDE_CODE_OAUTH_TOKEN w środowisku.")

    db.init()
    for article_id in db.pending_ids():  # dokończ to, co przerwał restart
        worker.enqueue(article_id)

    print(f"Wticzka: http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
