"""Szablony HTML interfejsu webowego."""
from html import escape
from urllib.parse import urlparse

from db import STATUSES

CSS = """
:root {
  --bg: #f7f5f0; --card: #ffffff; --text: #1f1f1f; --muted: #6b6b6b;
  --border: #e4e0d8; --accent: #1565c0; --ok: #2e7d32; --err: #c62828; --warn: #b26a00;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #161616; --card: #1f1f1f; --text: #e8e6e3; --muted: #9a9a9a;
    --border: #333; --accent: #64a8f0; --ok: #66bb6a; --err: #ef5350; --warn: #ffb74d;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
a { color: var(--accent); }
.wrap { max-width: 760px; margin: 0 auto; padding: 24px 16px 64px; }
header.top { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 20px; }
header.top h1 { font-size: 22px; margin: 0; }
header.top h1 a { color: inherit; text-decoration: none; }
header.top form { margin: 0; }
nav.tabs { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 20px; }
nav.tabs a {
  padding: 6px 14px; border-radius: 999px; text-decoration: none;
  color: var(--muted); border: 1px solid var(--border); background: var(--card);
}
nav.tabs a.active { color: #fff; background: var(--accent); border-color: var(--accent); }
.card {
  display: block; background: var(--card); border: 1px solid var(--border);
  border-radius: 12px; padding: 16px 18px; margin-bottom: 12px;
  text-decoration: none; color: inherit;
}
a.card:hover { border-color: var(--accent); }
.card h2 { font-size: 18px; margin: 0 0 6px; line-height: 1.3; }
.card p { margin: 0 0 8px; color: var(--muted); }
.meta { font-size: 13px; color: var(--muted); }
.badge { font-size: 12px; padding: 2px 8px; border-radius: 999px; border: 1px solid currentColor; }
.badge.pending { color: var(--warn); }
.badge.error { color: var(--err); }
.empty { color: var(--muted); text-align: center; padding: 48px 0; }
article .lead { font-size: 19px; color: var(--muted); margin: 0 0 8px; }
article h1 { font-size: 30px; line-height: 1.2; margin: 0 0 12px; }
.prose {
  font-family: Charter, "Iowan Old Style", Georgia, serif;
  font-size: 19px; line-height: 1.7;
}
.prose h2 {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 20px; margin: 36px 0 12px; padding-bottom: 6px; border-bottom: 1px solid var(--border);
}
.prose h3 { font-size: 19px; margin: 28px 0 8px; }
.prose blockquote { margin: 16px 0; padding-left: 16px; border-left: 3px solid var(--border); color: var(--muted); }
.prose pre { overflow-x: auto; background: var(--card); padding: 12px; border-radius: 8px; font-size: 14px; }
.prose table { border-collapse: collapse; width: 100%; font-size: 16px; }
.prose th, .prose td { border: 1px solid var(--border); padding: 6px 8px; text-align: left; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; margin: 20px 0; }
.actions form { margin: 0; }
button {
  font: inherit; font-size: 14px; padding: 7px 14px; border-radius: 8px; cursor: pointer;
  border: 1px solid var(--border); background: var(--card); color: var(--text);
}
form.add { display: flex; gap: 8px; margin-bottom: 16px; }
form.add input {
  flex: 1; min-width: 0; font: inherit; padding: 8px 12px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--card); color: var(--text);
}
button.primary { background: var(--ok); border-color: var(--ok); color: #fff; }
button.danger { color: var(--err); }
.error-box {
  background: var(--card); border: 1px solid var(--err); border-radius: 8px;
  padding: 12px; white-space: pre-wrap; font-size: 14px;
}
"""


def _layout(title, body, refresh=False):
    refresh_tag = '<meta http-equiv="refresh" content="5">' if refresh else ""
    return f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{refresh_tag}
<title>{escape(title)}</title>
<style>{CSS}</style>
</head>
<body><div class="wrap">
<header class="top"><h1><a href="/">📚 Wticzka</a></h1><form method="post" action="/hn"><button title="Pobierz teraz top z Hacker News">↻ HN</button></form></header>
{body}
</div></body>
</html>"""


def _domain(url):
    return urlparse(url).netloc.removeprefix("www.")


def _display_title(a):
    return a["title"] or a["page_title"] or a["url"]


def _state_badge(a):
    if a["state"] == "pending":
        return '<span class="badge pending">⏳ Claude pracuje…</span>'
    if a["state"] == "error":
        return '<span class="badge error">błąd</span>'
    return ""


def _button(article_id, action, label, value="", css=""):
    hidden = f'<input type="hidden" name="status" value="{value}">' if value else ""
    return (
        f'<form method="post" action="/article/{article_id}/{action}">{hidden}'
        f'<button class="{css}">{label}</button></form>'
    )


def list_page(status, articles, counts):
    tabs = "".join(
        f'<a href="/?status={key}" class="{"active" if key == status else ""}">'
        f"{label} ({counts[key]})</a>"
        for key, label in STATUSES.items()
    )
    if articles:
        cards = "".join(
            f"""<a class="card" href="/article/{a['id']}">
<h2>{escape(_display_title(a))}</h2>
{f'<p>{escape(a["lead"])}</p>' if a["lead"] else ""}
<div class="meta">{escape(_domain(a['url']))} · {escape(a['created_at'][:16])} {_state_badge(a)}</div>
</a>"""
            for a in articles
        )
    else:
        cards = '<div class="empty">Pusto.</div>'
    refresh = any(a["state"] == "pending" for a in articles)
    add_form = (
        '<form class="add" method="post" action="/add">'
        '<input type="url" name="url" placeholder="Wklej link…" required>'
        '<button class="primary">Dodaj</button></form>'
    )
    return _layout("Wticzka", f'{add_form}<nav class="tabs">{tabs}</nav>{cards}', refresh=refresh)


def article_page(a):
    i = a["id"]
    status_buttons = {
        "to_read": _button(i, "status", "✓ Przeczytane", "read", "primary")
        + _button(i, "status", "Archiwizuj", "archived"),
        "read": _button(i, "status", "↩ Do przeczytania", "to_read")
        + _button(i, "status", "Archiwizuj", "archived"),
        "archived": _button(i, "status", "↩ Do przeczytania", "to_read"),
    }[a["status"]]
    actions = (
        f'<div class="actions">{status_buttons}'
        f'{_button(i, "retry", "↻ Wygeneruj ponownie")}'
        f'{_button(i, "delete", "Usuń", css="danger")}</div>'
    )

    if a["state"] == "done":
        content = f'<div class="prose">{a["body_html"]}</div>'
    elif a["state"] == "pending":
        content = '<p class="empty">⏳ Claude czyta i tłumaczy… strona odświeży się sama.</p>'
    else:
        content = f'<p>Coś poszło nie tak:</p><div class="error-box">{escape(a["error"] or "")}</div>'

    body = f"""<p class="meta"><a href="/?status={a['status']}">← {STATUSES[a['status']]}</a></p>
<article>
<h1>{escape(_display_title(a))}</h1>
{f'<p class="lead">{escape(a["lead"])}</p>' if a["lead"] else ""}
<p class="meta"><a href="{escape(a['url'])}" rel="noreferrer">{escape(_domain(a['url']))} ↗</a>
· dodano {escape(a['created_at'][:16])}</p>
{actions}
{content}
{actions if a["state"] == "done" else ""}
</article>"""
    return _layout(_display_title(a), body, refresh=a["state"] == "pending")


def error_page(message):
    return _layout("Błąd", f'<div class="error-box">{escape(message)}</div><p><a href="/">← Wróć</a></p>')


def not_found_page():
    return _layout("Nie znaleziono", '<p class="empty">Nie ma takiego artykułu.</p>')
