from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import feedparser

DATA_FILE = "data.json"
RETENTION_DAYS = 7

# Sources mapped to categories (jobs/internships go into "jobs", rest into "articles")
SOURCES = [
    # 1. New Case Law & Judgments
    {
        "category": "New Case Law & Judgments",
        "kind": "article",
        "source": "LiveLaw",
        "url": "https://www.livelaw.in/google_feeds.xml",
    },
    {
        "category": "New Case Law & Judgments",
        "kind": "article",
        "source": "Bar & Bench",
        "url": "https://www.barandbench.com/rss",
    },
    # 2. Daily Current Affairs
    {
        "category": "Daily Current Affairs",
        "kind": "article",
        "source": "PIB National",
        "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1",
    },
    {
        "category": "Daily Current Affairs",
        "kind": "article",
        "source": "The Hindu National",
        "url": "https://www.thehindu.com/news/national/feeder/default.rss",
    },
    # 3. Jobs & Vacancies
    {
        "category": "Jobs & Vacancies",
        "kind": "job",
        "source": "FreeJobAlert",
        "url": "https://www.freejobalert.com/feed/",
    },
    # 4. Internships
    {
        "category": "Internships",
        "kind": "job",
        "source": "Lawctopus",
        "url": "https://lawctopus.com/feed",
    },
    {
        "category": "Internships",
        "kind": "job",
        "source": "iPleaders",
        "url": "https://blog.ipleaders.in/feed",
    },
    # 5. History Articles
    {
        "category": "History Articles",
        "kind": "article",
        "source": "Live History India",
        "url": "https://www.livehistoryindia.com/feed",
    },
    # 6. Science & Archaeology Research
    {
        "category": "Science & Archaeology Research",
        "kind": "article",
        "source": "ScienceDaily Archaeology",
        "url": "https://www.sciencedaily.com/rss/fossils_ruins.xml",
    },
    # 7. Parliament Activities
    {
        "category": "Parliament Activities",
        "kind": "article",
        "source": "PRS Legislative",
        "url": "https://prsindia.org/feed",
    },
    # 8. UP Vidhan Sabha & Parishad
    {
        "category": "UP Vidhan Sabha & Parishad",
        "kind": "article",
        "source": "PIB Lucknow",
        "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3",
    },
    # 9. Economics & Commerce
    {
        "category": "Economics & Commerce",
        "kind": "article",
        "source": "RBI",
        "url": "https://rbi.org.in/rssfeed.xml",
    },
    # 10. Crimes & Police Related Articles
    {
        "category": "Crimes & Police Related Articles",
        "kind": "article",
        "source": "PIB Home/Police",
        "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1",
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


def make_id(url: str, title: str) -> str:
  raw = f"{url.strip()}|{title.strip()}".encode("utf-8")
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
  with open(DATA_FILE, "r", encoding="utf-8") as f:
    return json.load(f)


def remove_old_items(items: list[dict], cutoff_date_str: str) -> list[dict]:
  return [
      item for item in items if item.get("date", "") >= cutoff_date_str
  ]


def run_update():
  today = datetime.now(timezone.utc).date()
  cutoff_str = (today - timedelta(days=RETENTION_DAYS)).isoformat()
  today_str = today.isoformat()

  data = load_existing_data()
  articles = remove_old_items(data.get("articles", []), cutoff_str)
  jobs = remove_old_items(data.get("jobs", []), cutoff_str)

  seen_article_ids = {item["id"] for item in articles if "id" in item}
  seen_job_ids = {item["id"] for item in jobs if "id" in item}

  for src in SOURCES:
    parsed = feedparser.parse(src["url"])
    for entry in parsed.entries[:10]:
      title = (entry.get("title") or "").strip()
      link = (entry.get("link") or "").strip()
      summary = (entry.get("summary") or "").strip()[:300]
      if not title or not link:
        continue

      item_id = make_id(link, title)
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
