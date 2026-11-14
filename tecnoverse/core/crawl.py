"""Fetch a company's homepage plus up to 7 linked pages. Returns cleaned text as SourcePage objects.

Raw HTML is cached in data/cache/<company_id>/. If a live fetch fails and a cached copy exists,
the cached copy is used and the crawl is reported as simulated.
"""
import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from core.schemas import Company, SourcePage
from core.store import CACHE
MAX_PAGES = 8
USER_AGENT = "TecnoVerseBot/0.1 (hackathon prototype)"
# English and Swedish words that mark pages worth reading for a company profile.
CORE = ["about", "om-oss", "om oss", "product", "produkt", "service", "tjanst", "tjänst", "solution", "losning",
        "lösning", "technolog", "teknik", "offer", "erbjud"]  # what the company does: weighted 3x
OTHER = ["project", "projekt", "case", "customer", "kund", "industr", "market", "segment", "news", "nyhet",
         "partner", "contact", "kontakt", "blog", "press", "aktuellt", "newsletter", "nyhetsbrev", "insight"]
NEWS = re.compile(r"news|nyhet|blog|press|aktuellt|newsletter|nyhetsbrev|insight", re.I)
CONTACT = re.compile(r"contact|kontakt", re.I)
SKIP = re.compile(r"\.(pdf|jpg|jpeg|png|gif|svg|zip|mp4|webp)$|/(wp-|tag/|category/|login|cart|privacy|cookie|gdpr|career|karriar|jobs?|jobb|lediga)", re.I)


def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


def _host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def clean(html: str) -> tuple[str, str]:
    """HTML -> (title, visible text)."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    for tag in soup(["script", "style", "noscript", "svg", "template", "iframe"]):
        tag.decompose()
    return title, re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def pick_links(html: str, base_url: str, limit: int = MAX_PAGES - 1) -> list[str]:
    """Same-site links whose URL or link text contains a keyword, best first."""
    scored: dict[str, int] = {}
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        url = urldefrag(urljoin(base_url, a["href"]))[0]
        if not url.startswith("http") or _host(url) != _host(base_url) or SKIP.search(url):
            continue
        if url.rstrip("/") == base_url.rstrip("/"):
            continue
        hay = (urlparse(url).path + " " + a.get_text(" ")).lower()
        score = 3 * sum(k in hay for k in CORE) + sum(k in hay for k in OTHER)
        if score:
            # shallow pages (/about) beat deep ones (/news/2021/some-post)
            score = score * 10 - urlparse(url).path.strip("/").count("/")
            scored[url] = max(score, scored.get(url, -99))
    ranked = sorted(scored, key=lambda u: (-scored[u], u))
    picked = ranked[:limit]
    # innovations come from news/blog pages and contacts from the contact page: make sure both get a slot
    for pattern in (NEWS, CONTACT):
        best = next((u for u in ranked if pattern.search(urlparse(u).path)), None)
        if best and best not in picked:
            picked = picked[:limit - 1] + [best]
    return picked


def _robots(base_url: str) -> RobotFileParser | None:
    rp = RobotFileParser()
    try:
        r = requests.get(urljoin(base_url, "/robots.txt"), headers={"User-Agent": USER_AGENT}, timeout=10)
        if r.status_code != 200:
            return None  # no robots.txt: allowed
        rp.parse(r.text.splitlines())
        return rp
    except requests.RequestException:
        return None


def _fetch(url: str, cache_dir, robots: RobotFileParser | None) -> tuple[str | None, bool]:
    """Returns (html, from_cache). Disallowed by robots.txt -> (None, False)."""
    if robots and not robots.can_fetch(USER_AGENT, url):
        return None, False
    cached = cache_dir / f"{_hash(url)}.html"
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        r.raise_for_status()
        if "charset" not in r.headers.get("content-type", "").lower():
            r.encoding = r.apparent_encoding  # requests assumes Latin-1 otherwise and garbles å ä ö
        if "html" not in r.headers.get("content-type", "html"):
            return None, False
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached.write_text(r.text, encoding="utf-8")
        return r.text, False
    except requests.RequestException:
        if cached.exists():
            return cached.read_text(encoding="utf-8"), True
        return None, False


def crawl(company: Company) -> tuple[list[SourcePage], bool]:
    """Returns (pages, simulated). simulated is True if any page came from the cache."""
    cache_dir = CACHE / company.id
    robots = _robots(company.website)
    pages: list[SourcePage] = []
    simulated = False

    def add(url: str) -> str | None:
        nonlocal simulated
        html, from_cache = _fetch(url, cache_dir, robots)
        if html is None:
            return None
        title, text = clean(html)
        if len(text) < 200 or any(p.content_hash == _hash(text) for p in pages):
            return html  # empty or duplicate page: not evidence
        simulated = simulated or from_cache
        pages.append(SourcePage(
            id=_hash(url), company_id=company.id, url=url, title=title, text=text,
            retrieved_at=datetime.now(timezone.utc), content_hash=_hash(text),
        ))
        return html

    home = add(company.website)
    if home:
        for url in pick_links(home, company.website):
            add(url)
    return pages, simulated


if __name__ == "__main__":  # self-check, no network: cd tecnoverse && python -m core.crawl
    html = """<html><title>Acme</title><script>x()</script><body>
      <a href="/about-us">About</a> <a href="/news/2021/old-post">News post</a>
      <a href="https://other.com/products">Elsewhere</a> <a href="/file.pdf">Products PDF</a>
      <a href="/products#top">Products</a> <a href="/random">Random</a></body></html>"""
    links = pick_links(html, "https://www.acme.se/")
    assert links[:2] == ["https://www.acme.se/about-us", "https://www.acme.se/products"], links
    assert "https://www.acme.se/news/2021/old-post" in links and len(links) == 3, links
    assert clean(html) == ("Acme", "Acme About News post Elsewhere Products PDF Products Random")
    print("ok")
