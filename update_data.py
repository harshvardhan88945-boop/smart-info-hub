from datetime import datetime, timedelta, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
import urllib.request
import feedparser

DATA_FILE = "data.json"
RETENTION_DAYS = 7

SOURCES = [
    # 1. New Case Law and Recent Judgement
    {
        "category": "New Case Law and Recent Judgement",
        "kind": "article",
        "source": "LiveLaw",
        "url": "https://www.livelaw.in/google_feeds.xml",
        "keywords": [],
        "fallback_all": True,
    },
    {
        "category": "New Case Law and Recent Judgement",
        "kind": "article",
        "source": "Bar & Bench",
        "url": "https://www.barandbench.com/feed",
        "keywords": [],
        "fallback_all": True,
    },
    # 2. Daily Current Affair
    {
        "category": "Daily Current Affair",
        "kind": "article",
        "source": "The Hindu National",
        "url": "https://www.thehindu.com/news/national/feeder/default.rss",
        "keywords": [],
        "fallback_all": True,
    },
    {
        "category": "Daily Current Affair",
        "kind": "article",
        "source": "Indian Express India",
        "url": "https://indianexpress.com/section/india/feed/",
        "keywords": [],
        "fallback_all": True,
    },
    # 3. Job and Vacancy (Sarkari Result + Multi-Source Jobs & Exams)
    {
        "category": "Job and Vacancy",
        "kind": "job",
        "source": "Sarkari Result Latest Jobs",
        "url": "https://www.sarkariresult.com/latestjob.php",
        "is_sarkari": True,
        "keywords": [],
        "fallback_all": True,
    },
    {
        "category": "Job and Vacancy",
        "kind": "job",
        "source": "Lawctopus Jobs",
        "url": "https://lawctopus.com/category/jobs/feed",
        "keywords": [],
        "fallback_all": True,
    },
    {
        "category": "Job and Vacancy",
        "kind": "job",
        "source": "Bar & Bench Jobs",
        "url": "https://www.barandbench.com/category/jobs/feed",
        "keywords": [],
        "fallback_all": True,
    },
    {
        "category": "Job and Vacancy",
        "kind": "job",
        "source": "FreeJobAlert",
        "url": "https://www.freejobalert.com/feed/",
        "keywords": [],
        "fallback_all": True,
    },
    {
        "category": "Job and Vacancy",
        "kind": "job",
        "source": "Jagran Josh Jobs",
        "url": "https://www.jagranjosh.com/rss/josh/jobs.xml",
        "keywords": [],
        "fallback_all": True,
    },
    {
        "category": "Job and Vacancy",
        "kind": "job",
        "source": "Indian Express Jobs",
        "url": "https://indianexpress.com/section/jobs/feed/",
        "keywords": [],
        "fallback_all": True,
    },
    {
        "category": "Job and Vacancy",
        "kind": "job",
        "source": "The Hindu Recruitment & Exams",
        "url": "https://www.thehindu.com/news/national/feeder/default.rss",
        "keywords": [
            "recruitment",
            "vacancy",
            "vacancies",
            "post",
            "posts",
            "exam",
            "examination",
            "upsc",
            "ssc",
            "judicial",
            "pcs-j",
            "pcs j",
            "apo",
            "prosecution",
            "apply",
            "bharti",
            "admit card",
            "result",
        ],
        "fallback_all": False,
    },
    # 4. Internship
    {
        "category": "Internship",
        "kind": "job",
        "source": "Lawctopus Internships",
        "url": "https://lawctopus.com/feed",
        "keywords": ["internship", "intern", "trainee", "stipend", "fellowship"],
        "fallback_all": True,
    },
    {
        "category": "Internship",
        "kind": "job",
        "source": "iPleaders Internships",
        "url": "https://blog.ipleaders.in/feed",
        "keywords": ["internship", "intern", "opportunity", "clerkship"],
        "fallback_all": False,
    },
    # 5. History Articles
    {
        "category": "History Articles",
        "kind": "article",
        "source": "Live History India",
        "url": "https://www.livehistoryindia.com/feed",
        "keywords": [],
        "fallback_all": True,
    },
    # 6. Science and New Research (Include Archaeology Research)
    {
        "category": "Science and New Research (Include Archaeology Research)",
        "kind": "article",
        "source": "ScienceDaily Fossils & Ruins",
        "url": "https://www.sciencedaily.com/rss/fossils_ruins.xml",
        "keywords": [],
        "fallback_all": True,
    },
    {
        "category": "Science and New Research (Include Archaeology Research)",
        "kind": "article",
        "source": "ScienceDaily Top Science",
        "url": "https://www.sciencedaily.com/rss/top/science.xml",
        "keywords": [
            "archaeology",
            "ancient",
            "excavation",
            "fossil",
            "research",
            "study",
            "discovery",
            "science",
        ],
        "fallback_all": False,
    },
    # 7. Parliament Update and Activities
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
            "adhiniyam",
            "sanhita",
        ],
        "fallback_all": True,
    },
    # 8. UP Vidhan Sabha, Vidhan Parishad News and Activities
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
            "legislative",
            "allahabad",
            "prayagraj",
            "yogi",
            "high court",
            "uppsc",
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
        "fallback_all": True,
    },
    {
        "category": "Economics and Commerce Article",
        "kind": "article",
        "source": "Financial Express",
        "url": "https://www.financialexpress.com/feed/",
        "keywords": [],
        "fallback_all": True,
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
        "bar council",
        "judiciary",
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
        "b.tech",
        "degree",
        "bachelor",
    ],
    "Post Graduation": [
        "llm",
        "m.a",
        "ma",
        "m.sc",
        "msc",
        "post graduate",
        "pg",
        "master",
        "phd",
    ],
}

STATE_RULES = {
    "Uttar Pradesh": [
        "uttar pradesh",
        "uppsc",
        "up pcs",
        "up apo",
        "allahabad",
        "prayagraj",
        "lucknow",
        "vidhan sabha",
        "vidhan parishad",
        "upsssc",
        "up police",
        "bharti",
    ],
    "All India": [
        "all india",
        "upsc",
        "ssc",
        "supreme court",
        "parliament",
        "central govt",
        "india",
        "sarkari",
        "ibps",
        "rbi",
    ],
}


class SimpleLinkParser(HTMLParser):

  def __init__(self):
    super().__init__()
    self.in_a = False
    self.current_href = ""
    self.current_text = []
    self.links = []

  def handle_starttag(self, tag, attrs):
    if tag == "a":
      self.in_a = True
      self.current_href = ""
      self.current_text = []
      for k, v in attrs:
        if k == "href" and v:
          self.current_href = v.strip()

  def handle_data(self, data):
    if self.in_a:
      self.current_text.append(data)

  def handle_endtag(self, tag):
    if tag == "a" and self.in_a:
      self.in_a = False
      title = " ".join("".join(self.current_text).split()).strip()
      if len(title) >= 8 and self.current_href.startswith("http"):
        self.links.append((title, self.current_href, title[:300]))


def fetch_sarkari_result_entries(
    url: str = "https://www.sarkariresult.com/latestjob.php",
) -> list[tuple[str, str, str]]:
  try:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
      html = resp.read().decode("utf-8", errors="ignore")

    parser = SimpleLinkParser()
    parser.feed(html)

    results = []
    seen_titles = set()
    for title, link, summary in parser.links:
      low = title.lower()
      if any(
          k in low
          for k in [
              "recruitment",
              "vacancy",
              "form",
              "exam",
              "result",
              "admit card",
              "post",
              "bharti",
              "apply",
              "online",
          ]
      ):
        if low not in seen_titles:
          seen_titles.add(low)
          results.append((title, link, summary))
      if len(results) >= 20:
        break
    return results
  except Exception as e:
    print(f"[Sarkari Result Fetch Note]: {e}")
    return []


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
  try:
    parsed = feedparser.parse(src["url"])
    entries = getattr(parsed, "entries", []) or []
  except Exception as e:
    print(f"[Feed Fetch Note - {src['source']}]: {e}")
    return []

  keywords = [k.lower() for k in src.get("keywords", [])]
  fallback_all = bool(src.get("fallback_all", False))

  matched = []
  all_valid = []

  for entry in entries[:30]:
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
      return matched[:15]
    if fallback_all:
      return all_valid[:15]
    return []

  return matched[:15]


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
    if src.get("is_sarkari"):
      chosen = fetch_sarkari_result_entries(src["url"])
    else:
      chosen = collect_entries_for_source(src)

    print(f"[{src['category']}] ({src['source']}) -> {len(chosen)} items fetched")

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
      f"DONE. Total Articles: {len(articles)}, Total Jobs: {len(jobs)} (Cutoff:"
      f" {cutoff_str})"
  )


if __name__ == "__main__":
  run_update()
          
