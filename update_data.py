from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import feedparser

DATA_FILE = "data.json"
RETENTION_DAYS = 7

# Reliable RSS sources mapped to the 9 categories
SOURCES = [
    # 1. New Case Law and Recent Judgement
    {
        "category": "New Case Law and Recent Judgement",
        "kind": "article",
        "source": "LiveLaw",
        "url": "https://www.livelaw.in/google_feeds.xml",
        "keywords": [],
    },
    # 2. Daily Current Affair
    {
        "category": "Daily Current Affair",
        "kind": "article",
        "source": "The Hindu National",
        "url": "https://www.thehindu.com/news/national/feeder/default.rss",
        "keywords": [],
    },
    # 3. Job and Vacancy
    {
        "category": "Job and Vacancy",
        "kind": "job",
        "source": "FreeJobAlert",
        "url": "https://www.freejobalert.com/feed/",
        "keywords": [],
    },
    # 4. Internship
    {
        "category": "Internship",
        "kind": "job",
        "source": "Lawctopus",
        "url": "https://lawctopus.com/feed",
        "keywords": [],
    },
    {
        "category": "Internship",
        "kind": "job",
        "source": "iPleaders",
        "url": "https://blog.ipleaders.in/feed",
        "keywords": [],
    },
    # 5. History Articles
    {
        "category": "History Articles",
        "kind": "article",
        "source": "Live History India",
        "url": "https://www.livehistoryindia.com/feed",
        "keywords": [],
    },
    # 6. Science and New Research (Include Archaeology Research)
    {
        "category": "Science and New Research (Include Archaeology Research)",
        "kind": "article",
        "source": "ScienceDaily Archaeology",
        "url": "https://www.sciencedaily.com/rss/fossils_ruins.xml",
        "keywords": [],
    },
    # 7. Parliament Update and Activities (The Hindu National + LiveLaw filtered for Parliament, with fallback)
    {
        "category": "Parliament Update and Activities",
        "kind": "article",
        "source": "The Hindu Parliament",
        "url": "https://www.thehindu.com/news/national/feeder/default.rss",
        "keywords": [
            "parliament",
            "lok sabha",
            "rajya sabha",
            "bill",
            "act",
            "session",
            "mp",
            "speaker",
            "constitution",
        ],
        "fallback_all": True,
    },
    # 8. UP Vidhan Sabha, Vidhan Parishad News and Activities (The Hindu National + LiveLaw filtered for UP/Assembly, with fallback)
    {
        "category": "UP Vidhan Sabha, Vidhan Parishad News and Activities",
        "kind": "article",
        "source": "UP & Assembly Updates",
        "url": "https://www.thehindu.com/news/national/feeder/default.rss",
        "keywords": [
            "uttar pradesh",
            "up ",
            "lucknow",
            "vidhan sabha",
            "vidhan parishad",
            "assembly",
            "allahabad",
            "yogi",
            "high court",
        ],
        "fallback_all": True,
    },
    # 9. Economics and Commerce Article
    {
        "category": "Economics and Commerce Article",
        "kind": "article",
        "source": "The Hindu Business",
        "url": "https://www.thehindu.com/business/feeder/default.rss",
        "keywords": [],
    },
]

QUALIFICATION_RULES = {
    "LLB": [
        "llb",
        "law",
        "judicial",
        "pcs-j",
        "pcs j",
        "apo",
        "prosecution",
        "legal",
        "advocate",
        "court",
    ],
    "Graduation": [
        "graduate",
        "graduation",
        "b.a",
        "ba",
        "b.sc",
        "bsc",
        "b.com",
        "bcom",
        "any degree",
    ],
    "Post Graduation": ["llm", "m.a", "ma", "m.sc", "msc", "post graduate", "pg"],
}

STATE_RULES = {
    "Uttar Pradesh": [
        "uttar pradesh",
        "uppsc",
        "up pcs",
        "up apo",
        "allahabad",
        "lucknow",
        "vidhan sabha",
        "vidhan parishad",
    ],
    "All India": [
        "all india",
        "upsc",
        "ssc",
        "supreme court",
        "parliament",
        "central govt",
        "india",
    ],
}


def make_id(category: str, url: str, title: str) -> str:
  raw = f"{category.strip()}|{url.strip()}|{title.strip()}".encode("utf-8")
  return hashlib.md5(raw).hexdigest()[:12]


def detect_qualifications(text: str) -> list[str]:
  low = text.lower()
  matched = [
      qual
      for qual, words in QUALIFICATION_RULES.items()
      if any(w in low for w in words)
  ]
  return matched if matched else ["General"]


def detect_state(text: str) -> str:
  low = text.lower()
  for state, words in STATE_RULES.items():
    if any(w in low for w in words):
      return state
  return "Other / Unspecified"


def load_existing_data() -> dict:
  if not os.path.exists(DATA_FILE):
    return {"last_updated": "", "articles": [], "jobs": []}
  try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
      loaded = json.load(f)
      if isinstance(loaded, dict):
        return loaded
  except Exception:
    pass
  return {"last_updated": "", "articles": [], "jobs": []}


def remove_old_items(items: list[dict], cutoff_date_str: str) -> list[dict]:
  return [item for item in items if item.get("date", "") >= cutoff_date_str]


def collect_entries_for_source(src: dict) -> list[tuple[str, str, str]]:
  parsed = feedparser.parse(src["url"])
  entries = getattr(parsed, "entries", []) or []
  keywords = [k.lower() for k in src.get("keywords", [])]
  fallback_all = bool(src.get("fallback_all", False))

  matched = []
  all_valid = []

  for entry in entries[:25]:
    title = (entry.get("title") or "").strip()
    link = (entry.get("link") or "").strip()
    summary = (entry.get("summary") or "").strip()[:300]
    if not title or not link:
      continue

    all_valid.append((title, link, summary))
    if not keywords:
      matched.append((title, link, summary))
    else:
      haystack = f"{title} {summary}".lower()
      if any(kw in haystack for kw in keywords):
        matched.append((title, link, summary))

  if keywords:
    if matched:
      return matched[:10]
    if fallback_all:
      return all_valid[:10]
    return []

  return matched[:10]


def run_update():
  today = datetime.now(timezone.utc).date()
  cutoff_str = (today - timedelta(days=RETENTION_DAYS)).isoformat()
  today_str = today.isoformat()

  existing = load_existing_data()
  articles = remove_old_items(existing.get("articles", []), cutoff_str)
  jobs = remove_old_items(existing.get("jobs", []), cutoff_str)

  seen_article_ids = {item.get("id") for item in articles if item.get("id")}
  seen_job_ids = {item.get("id") for item in jobs if item.get("id")}

  for src in SOURCES:
    chosen = collect_entries_for_source(src)
    print(f"[{src['category']}] ({src['source']}) -> {len(chosen)} entries")

    for title, link, summary in chosen:
      item_id = make_id(src["category"], link, title)
      combined_text = f"{title} {summary} {src['category']}"

      if src["kind"] == "job":
        if item_id in seen_job_ids:
          continue
        jobs.append({
            "id": item_id,
            "category": src["category"],
            "title": title,
            "qualifications": detect_qualifications(combined_text),
            "state": detect_state(combined_text),
            "source": src["source"],
            "url": link,
            "date": today_str,
        })
        seen_job_ids.add(item_id)
      else:
        if item_id in seen_article_ids:
          continue
        articles.append({
            "id": item_id,
            "category": src["category"],
            "title": title,
            "summary": summary,
            "source": src["source"],
            "url": link,
            "date": today_str,
        })
        seen_article_ids.add(item_id)

  output = {
      "last_updated": datetime.now(timezone.utc).isoformat(),
      "articles": articles,
      "jobs": jobs,
  }
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

  print(
      f"Done. Articles: {len(articles)}, Jobs: {len(jobs)} (Removed items"
      f" before {cutoff_str})"
  )


if __name__ == "__main__":
  run_update()
    
