import json
import re
import datetime
import urllib.request
import xml.etree.ElementTree as ET

CATEGORIES = [
    "New Case Law and Recent Judgement",
    "Daily Current Affair",
    "Job and Vacancy",
    "Internship",
    "History Articles",
    "Science and New Research (Include Archaeology Research)",
    "Parliament Update and Activities",
    "UP Vidhan Sabha, Vidhan Parishad News and Activities",
    "Economics and Commerce Article"
]

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

def classify_item(title, description, link):
    text = (title + " " + description).lower()
    
    # 1. Internship Logic
    if any(k in text for k in ["internship", "intern", "clerkship", "legal intern"]):
        return "Internship"
        
    # 2. Case Law & Judgements
    if any(k in text for k in ["supreme court", "high court", "judgement", "judgment", "ruling", "bench", "held that", "precedent", "quashed"]):
        return "New Case Law and Recent Judgement"
        
    # 3. Science & Archaeology
    if any(k in text for k in ["archaeology", "excavation", "asi", "isro", "research", "discovery", "bhatnagar award", "nobel prize", "science"]):
        return "Science and New Research (Include Archaeology Research)"
        
    # 4. UP Vidhan Sabha / Parishad
    if any(k in text for k in ["up vidhan", "vidhan sabha", "vidhan parishad", "uttar pradesh assembly"]):
        return "UP Vidhan Sabha, Vidhan Parishad News and Activities"
        
    # 5. Parliament
    if any(k in text for k in ["parliament", "lok sabha", "rajya sabha", "bill passed", "parliamentary"]):
        return "Parliament Update and Activities"
        
    # 6. History
    if any(k in text for k in ["history", "ancient", "medieval", "freedom struggle", "archaeological survey"]):
        return "History Articles"
        
    # 7. Economics & Commerce
    if any(k in text for k in ["rbi", "economy", "economics", "gdp", "gst", "inflation", "sebi", "commerce"]):
        return "Economics and Commerce Article"
        
    # 8. Jobs & Vacancies
    if any(k in text for k in ["recruitment", "vacancy", "post", "civil judge", "apo", "legal officer", "notification"]):
        return "Job and Vacancy"
        
    # Default fallback
    return "Daily Current Affair"

def extract_qualifications(text):
    text_lower = text.lower()
    quals = []
    if "llb" in text_lower or "law" in text_lower or "advocate" in text_lower:
        quals.append("LLB")
    if "post grad" in text_lower or "llm" in text_lower or "master" in text_lower:
        quals.append("Post Graduation")
    if "graduat" in text_lower or "degree" in text_lower:
        quals.append("Graduation")
    if not quals:
        quals.append("General")
    return list(set(quals))

def extract_state(text):
    text_lower = text.lower()
    if "uttar pradesh" in text_lower or "up " in text_lower or "allahabad" in text_lower or "lucknow" in text_lower:
        return "Uttar Pradesh"
    return "All India"

def fetch_rss_feeds():
    # Aapke zaroori sources ke RSS Feeds
    feeds = [
        # Legal & Internship Feeds
        ("https://www.livelaw.in/rss/feed.xml", "LiveLaw"),
        ("https://www.barandbench.com/feed", "Bar & Bench"),
        ("https://www.lawctopus.com/feed/", "Lawctopus"),
        # Current Affairs & Research Feeds
        ("https://pib.gov.in/RssFeed.aspx", "PIB India"),
        ("https://thewire.in/rss", "The Wire"),
        ("https://frontline.thehindu.com/feeder/default.rss", "Frontline"),
    ]
    
    jobs = []
    articles = []
    item_id = 1
    
    for feed_url, source_name in feeds:
        try:
            req = urllib.request.Request(feed_url, headers={'User-Agent': 'Mozilla/5.0'})
            xml_data = urllib.request.urlopen(req, timeout=10).read()
            root = ET.fromstring(xml_data)
            
            # Channel items parse karna
            for item in root.findall('.//item'):
                title = clean_text(item.findtext('title'))
                link = clean_text(item.findtext('link'))
                desc = clean_text(item.findtext('description'))
                pub_date = clean_text(item.findtext('pubDate'))
                
                if not title or not link:
                    continue
                
                category = classify_item(title, desc, link)
                today_str = datetime.date.today().strftime("%Y-%m-%d")
                
                if category in ["Job and Vacancy", "Internship"]:
                    jobs.append({
                        "id": f"job_{item_id}",
                        "kind": "job" if category == "Job and Vacancy" else "internship",
                        "category": category,
                        "title": title,
                        "source": source_name,
                        "url": link,
                        "date": today_str,
                        "qualifications": extract_qualifications(title + " " + desc),
                        "state": extract_state(title + " " + desc)
                    })
                else:
                    articles.append({
                        "id": f"art_{item_id}",
                        "kind": "article",
                        "category": category,
                        "title": title,
                        "source": source_name,
                        "url": link,
                        "date": today_str
                    })
                item_id += 1
        except Exception as e:
            print(f"Error fetching {source_name}: {e}")

    output_data = {
        "last_updated": datetime.datetime.utcnow().isoformat(),
        "jobs": jobs,
        "articles": articles
    }
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print("data.json updated successfully!")

if __name__ == "__main__":
    fetch_rss_feeds()
