import datetime
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

DATA_FILE = "data.json"

CATEGORIES = [
    "New Case Law and Recent Judgement",
    "Daily Current Affair",
    "Job and Vacancy",
    "Internship",
    "History Articles",
    "Science and New Research (Include Archaeology Research)",
    "Parliament Update and Activities",
    "UP Vidhan Sabha, Vidhan Parishad News and Activities",
    "Economics and Commerce Article",
]

RSS_FEEDS = [
    ("https://www.livelaw.in/rss/feed.xml", "LiveLaw", "New Case Law and Recent Judgement"),
    ("https://www.barandbench.com/feed", "Bar & Bench", "New Case Law and Recent Judgement"),
    ("https://www.lawctopus.com/feed/", "Lawctopus", "Internship"),
    ("https://pib.gov.in/RssFeed.aspx", "PIB India", "Daily Current Affair"),
    ("https://frontline.thehindu.com/feeder/default.rss", "Frontline", "History Articles"),
]

SEARCH_QUERIES = [
    (
        '("legal internship" OR "law internship") ("Ministry of Law" OR "Supreme Court" OR "High Court" OR "insurance") India',
        "Google News Search",
        "Internship",
    ),
    (
        '("Supreme Court" OR "High Court") ("judgment" OR "ruling" OR "precedent" OR "held") India',
        "Google News Search",
        "New Case Law and Recent Judgement",
    ),
    (
        '("science research" OR "discovery" OR "archaeology" OR "excavation" OR "award") India',
        "Google News Search",
        "Science and New Research (Include Archaeology Research)",
    ),
    (
        '("recruitment" OR "vacancy" OR "notification") ("India" OR "Uttar Pradesh")',
        "Google News Search",
        "Job and Vacancy",
    ),
    (
        '("Parliament" OR "Lok Sabha" OR "Rajya Sabha") ("bill" OR "session" OR "committee") India',
        "Google News Search",
        "Parliament Update and Activities",
    ),
    (
        '("Vidhan Sabha" OR "Vidhan Parishad") ("Uttar Pradesh" OR "UP")',
        "Google News Search",
        "UP Vidhan Sabha, Vidhan Parishad News and Activities",
    ),
    (
        '("RBI" OR "economy" OR "commerce" OR "GST" OR "trade") India',
        "Google News Search",
        "Economics and Commerce Article",
    ),
    (
        '("current affairs" OR "important news") India',
        "Google News Search",
        "Daily Current Affair",
    ),
]


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_title_key(title):
    t = re.sub(r"[^a-z0-9\s]", "", (title or "").lower())
    t = re.sub(r"\s+", " ", t).strip()
    return t


def is_excluded(text):
    t = (text or "").lower()
    blocked = ["admit card", "answer key", "result out", "horoscope"]
    return any(b in t for b in blocked)


def classify_item(title, description, default_category):
    text = f"{title} {description}".lower()

    if any(k in text for k in ["internship", "intern", "clerkship", "legal intern"]):
        return "Internship"
    if any(k in text for k in ["supreme court", "high court", "judgement", "judgment", "ruling", "precedent", "held that"]):
        return "New Case Law and Recent Judgement"
    if any(k in text for k in ["archaeology", "excavation", "asi", "isro", "research", "discovery", "nobel", "award"]):
        return "Science and New Research (Include Archaeology Research)"
    if any(k in text for k in ["vidhan sabha", "vidhan parishad", "uttar pradesh assembly"]):
        return "UP Vidhan Sabha, Vidhan Parishad News and Activities"
    if any(k in text for k in ["parliament", "lok sabha", "rajya sabha", "parliamentary"]):
        return "Parliament Update and Activities"
    if any(k in text for k in ["history", "ancient", "medieval", "freedom struggle"]):
        return "History Articles"
    if any(k in text for k in ["rbi", "economy", "economics", "commerce", "gdp", "gst", "sebi"]):
        return "Economics and Commerce Article"
    if any(k in text for k in ["recruitment", "vacancy", "notification", "civil judge", "apo"]):
        return "Job and Vacancy"

    return default_category if default_category in CATEGORIES else "Daily Current Affair"


def extract_qualifications(text):
    t = (text or "").lower()
    quals = []
    if any(k in t for k in ["llb", "law", "advocate", "judicial", "apo"]):
        quals.append("LLB")
    if any(k in t for k in ["post grad", "llm", "m.a.", "m.sc", "master"]):
        quals.append("Post Graduation")
    if any(k in t for k in ["graduat", "b.a.", "b.sc", "b.com", "degree"]):
        quals.append("Graduation")
    if not quals:
        quals.append("General")
    return sorted(set(quals))


def extract_state(text):
    t = (text or "").lower()
    if any(k in t for k in ["uttar pradesh", " up ", "allahabad", "lucknow", "varanasi", "kanpur", "agra"]):
        return "Uttar Pradesh"
    if any(k in t for k in ["all india", "government of india", "ministry of", "supreme court of india"]):
        return "All India"
    return "Other / Unspecified"


def build_google_news_rss_url(query):
    encoded = urllib.parse.quote_plus(query)
    return f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"


def parse_rss_url(feed_url, source_name, default_category):
    items = []
    try:
        req = urllib.request.Request(
            feed_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        xml_data = urllib.request.urlopen(req, timeout=15).read()
        root = ET.fromstring(xml_data)

        for node in root.findall(".//item"):
            title = clean_text(node.findtext("title"))
            link = clean_text(node.findtext("link"))
            desc = clean_text(node.findtext("description"))
            if not title or not link:
                continue
            if is_excluded(f"{title} {desc}"):
                continue

            category = classify_item(title, desc, default_category)
            items.append({
                "category": category,
                "title": title,
                "source": source_name,
                "url": link,
                "desc": desc,
            })
    except Exception as e:
        print(f"[WARN] Feed failed ({source_name}): {e}")
    return items


def load_existing_data():
    if not os.path.exists(DATA_FILE):
        return {"jobs": [], "articles": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "jobs": data.get("jobs", []) if isinstance(data.get("jobs"), list) else [],
                "articles": data.get("articles", []) if isinstance(data.get("articles"), list) else [],
            }
    except Exception as e:
        print(f"[WARN] Could not read existing {DATA_FILE}: {e}")
        return {"jobs": [], "articles": []}


def run_reader():
    existing = load_existing_data()
    jobs = list(existing["jobs"])
    articles = list(existing["articles"])

    seen_urls = set()
    seen_titles = set()
    max_num = 0

    for entry in jobs + articles:
        u = (entry.get("url") or "").strip()
        tk = normalize_title_key(entry.get("title") or "")
        if u:
            seen_urls.add(u)
        if tk:
            seen_titles.add(tk)
        m = re.search(r"(\d+)$", str(entry.get("id") or ""))
        if m:
            max_num = max(max_num, int(m.group(1)))

    collected = []
    for feed_url, source_name, default_cat in RSS_FEEDS:
        collected.extend(parse_rss_url(feed_url, source_name, default_cat))

    for query, source_name, default_cat in SEARCH_QUERIES:
        search_rss_url = build_google_news_rss_url(query)
        collected.extend(parse_rss_url(search_rss_url, source_name, default_cat))

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    added_count = 0

    for raw in collected:
        u = raw["url"].strip()
        tk = normalize_title_key(raw["title"])
        if not tk or u in seen_urls or tk in seen_titles:
            continue

        seen_urls.add(u)
        seen_titles.add(tk)
        max_num += 1
        cat = raw["category"]

        if cat in ("Job and Vacancy", "Internship"):
            jobs.append({
                "id": f"job_{max_num}",
                "kind": "job" if cat == "Job and Vacancy" else "internship",
                "category": cat,
                "title": raw["title"],
                "source": raw["source"],
                "url": u,
                "date": today_str,
                "qualifications": extract_qualifications(f"{raw['title']} {raw['desc']}"),
                "state": extract_state(f"{raw['title']} {raw['desc']}"),
            })
        else:
            articles.append({
                "id": f"art_{max_num}",
                "kind": "article",
                "category": cat,
                "title": raw["title"],
                "source": raw["source"],
                "url": u,
                "date": today_str,
            })
        added_count += 1

    output = {
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "jobs": jobs,
        "articles": articles,
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Done. Added {added_count} new items. Total jobs={len(jobs)}, articles={len(articles)}")


if __name__ == "__main__":
    run_reader()
