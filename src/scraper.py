import re
import time
import random
import html
from datetime import datetime
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "JobMonitorBot/1.0 (+https://github.com/<OWNER>/<REPO>)"
}
DELAY_RANGE = (1.0, 3.0)
MAX_PAGES = 1  # zwiększ, jeśli potrzebne

KEYWORDS = [
    "Chief Accountant",
    "Główna księgowa",
    "Główny księgowy",
]

def _sleep():
    time.sleep(random.uniform(*DELAY_RANGE))

def fetch(url):
    _sleep()
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def norm_text(x):
    return re.sub(r"\s+", " ", html.unescape((x or "").strip()))

def parse_date_iso(raw):
    # próby parsowania typowych formatów (YYYY-MM-DD, DD.MM.YYYY, „dzisiaj/wczoraj” – tu mapowane na dziś/wczoraj)
    raw = (raw or "").strip().lower()
    today = datetime.utcnow().date()
    if raw in {"dzisiaj", "today"}:
        return today.isoformat()
    if raw == "wczoraj":
        return (today - datetime.timedelta(days=1)).isoformat()
    # spróbuj ISO
    try:
        return datetime.fromisoformat(raw[:10]).date().isoformat()
    except Exception:
        pass
    # spróbuj DD.MM.YYYY
    m = re.match(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})", raw)
    if m:
        d, mth, y = m.groups()
        y = int(y) if len(y) == 4 else (2000 + int(y))
        return datetime(y, int(mth), int(d)).date().isoformat()
    # fallback: brak daty → dzisiejsza
    return today.isoformat()

def build_queries():
    # Każde źródło: wygeneruj listę URL-i dla słów kluczowych
    q = []
    for kw in KEYWORDS:
        kw_q = quote_plus(kw)
        # pracuj.pl: wyszukiwarka ofert (PL)
        q.append(("pracuj.pl",
                  f"https://www.pracuj.pl/praca/{kw_q};kw?rd=0"))
        # rocketjobs.pl: search
        q.append(("rocketjobs.pl",
                  f"https://rocketjobs.pl/s?q={kw_q}"))
        # indeed: Polska
        q.append(("pl.indeed.com",
                  f"https://pl.indeed.com/jobs?q={kw_q}&l=Polska"))
    return q

def scrape_pracuj(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    items = []
    # TODO: doprecyzuj selektor kart oferty (przykładowo artykuły/listingi)
    for card in soup.select("div[data-test='default-offer']"):
        title_el = card.select_one("[data-test='offer-title']")
        title = norm_text(title_el.get_text()) if title_el else None
        url_el = card.select_one("a[href]")
        url = url_el["href"] if url_el else None
        if url and url.startswith("/"):
            url = urljoin("https://www.pracuj.pl", url)
        company_el = card.select_one("[data-test='text-company-name']")
        company = norm_text(company_el.get_text()) if company_el else None
        # Data publikacji – często w znaczniku time lub labelu
        date_el = card.select_one("time") or card.select_one("[data-test='text-added-time']")
        pub_date = parse_date_iso(date_el.get("datetime") if date_el and date_el.has_attr("datetime")
                                  else (date_el.get_text() if date_el else None))
        items.append({
            "company": company,
            "company_website": "",
            "industry": "",
            "job_title": title,
            "pub_date": pub_date,
            "job_url": url,
            "source": "pracuj.pl"
        })
    return items

def scrape_rocketjobs(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    items = []
    # TODO: doprecyzuj selektor listingu
    for card in soup.select("a[href*='/oferta/'], a[href*='/praca/']"):
        url = card.get("href")
        if url and url.startswith("/"):
            url = urljoin("https://rocketjobs.pl", url)
        title = norm_text(card.get_text())
        # Rocketjobs: firma bywa w sąsiednich elementach
        parent = card.find_parent()
        company_el = parent.select_one("div:has(svg) + span, [data-testid='company-name']") if parent else None
        company = norm_text(company_el.get_text()) if company_el else ""
        # Data bywa ukryta/relatywna – zostaw pustą lub „dzisiaj”
        pub_date = parse_date_iso("")
        items.append({
            "company": company,
            "company_website": "",
            "industry": "",
            "job_title": title,
            "pub_date": pub_date,
            "job_url": url,
            "source": "rocketjobs.pl"
        })
    return items

def scrape_indeed(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    items = []
    # TODO: doprecyzuj selektor listingu Indeed (wyniki to <a> z jobTitle / karta wyników)
    for card in soup.select("a.tapItem"):
        url = card.get("href")
        if url and url.startswith("/"):
            url = urljoin("https://pl.indeed.com", url)
        title_el = card.select_one("h2.jobTitle span")
        title = norm_text(title_el.get_text()) if title_el else ""
        company_el = card.select_one("span.companyName")
        company = norm_text(company_el.get_text()) if company_el else ""
        date_el = card.select_one("span.date, span.result-footer span")
        pub_date = parse_date_iso(date_el.get_text() if date_el else "")
        items.append({
            "company": company,
            "company_website": "",
            "industry": "",
            "job_title": title,
            "pub_date": pub_date,
            "job_url": url,
            "source": "pl.indeed.com"
        })
    return items

def scrape_all():
    results = []
    for source, url in build_queries():
        try:
            html_text = fetch(url)
            if source == "pracuj.pl":
                results.extend(scrape_pracuj(html_text))
            elif source == "rocketjobs.pl":
                results.extend(scrape_rocketjobs(html_text))
            elif source == "pl.indeed.com":
                results.extend(scrape_indeed(html_text))
        except Exception as e:
            # log i kontynuacja
            print(f"[WARN] {source} failed: {e}")
    # Filtruj dokładniej po słowach kluczowych w tytule (bezpiecznik)
    kw_re = re.compile("|".join([re.escape(k) for k in KEYWORDS]), re.IGNORECASE)
    results = [r for r in results if r.get("job_title") and kw_re.search(r["job_title"])]
    # Usuń rekordy bez URL
    results = [r for r in results if r.get("job_url")]
    return results
