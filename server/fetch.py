"""Pobieranie strony po URL (dla linków dodanych ręcznie, np. z telefonu)."""
import ipaddress
import socket
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse

MAX_BYTES = 5 * 1024 * 1024
TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"

SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "nav", "footer", "header", "aside", "form"}
BLOCK_TAGS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "blockquote", "pre", "section", "article"}


def check_url(url):
    """Tylko http(s) i tylko publiczne adresy: serwer stoi w VPN-ie,
    więc nie może dać się użyć do zaglądania w sieć wewnętrzną."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Obsługiwane są tylko adresy http(s)://")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
    except socket.gaierror as err:
        raise ValueError(f"Nie znam hosta {parsed.hostname}") from err
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ValueError(f"Adres {parsed.hostname} nie jest publiczny")


class _SafeRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_SafeRedirects)


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.parts = []
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            self.parts.append(data)

    def text(self):
        lines = (" ".join(line.split()) for line in "".join(self.parts).splitlines())
        return "\n".join(line for line in lines if line)


def fetch_page(url):
    """Zwraca (tytuł, tekst) strony."""
    check_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pl,en;q=0.8"})
    with _opener.open(req, timeout=TIMEOUT) as res:
        content_type = res.headers.get_content_type()
        if content_type not in ("text/html", "application/xhtml+xml", "text/plain"):
            raise ValueError(f"To nie jest strona HTML ({content_type})")
        raw = res.read(MAX_BYTES + 1)[:MAX_BYTES]
        charset = res.headers.get_content_charset() or "utf-8"

    html = raw.decode(charset, errors="replace")
    if content_type == "text/plain":
        return "", html

    parser = _TextExtractor()
    parser.feed(html)
    text = parser.text()
    if not text:
        raise ValueError("Nie udało się wyciągnąć tekstu ze strony (może wymaga JavaScriptu?)")
    return " ".join(parser.title.split()), text
