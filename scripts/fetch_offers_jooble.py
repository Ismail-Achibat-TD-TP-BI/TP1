import json, os, re, time
import requests

# Jooble API -- a real, officially-issued key (course-provided), not an
# unauthorized scrape. Replaces France Travail as the primary acquisition
# source in this pipeline: France Travail's "Offres d'emploi v2" scope was
# not granted on this course's francetravail.io application (confirmed by a
# real token request returning invalid_client), while this key was confirmed
# working on a real test call (83,077 total matches for "stage informatique",
# 30 real postings returned, e.g. Thales, ArianeGroup, S3NS).
#
# Two honest limits, stated here because they shape everything downstream:
# 1. The key is capped at 500 requests TOTAL for its lifetime, not per day --
#    confirmed in Jooble's own confirmation email. A weekly scheduled fetch
#    uses one call per run, so a full term (~12-15 weeks) stays well inside
#    budget -- but repeated manual testing/debugging eats into the same pool,
#    so this script fetches ONE page per run, never loops over pages.
# 2. Jooble returns a short, pre-truncated "snippet" (~300 chars, with "..."
#    and residual HTML like "<b>" / "&nbsp;"), not the full posting text
#    France Travail would have given. extract_offers.py's LLM step only ever
#    sees what's in this snippet -- expect weaker/less specific
#    required_skills, responsibilities, experience_required and
#    compensation_mentioned than the manual's own France-Travail-based
#    examples, not a bug in that script.

API_KEY = os.environ["JOOBLE_API_KEY"]
HOST = "https://fr.jooble.org/api/"
SEARCH_PARAMS = {"keywords": "stage informatique", "location": "France"}

TAG_RE = re.compile(r"<[^>]+>")

def clean_snippet(text):
    # Strip Jooble's highlight tags (<b>...</b>) and the &nbsp; entities it
    # leaves in -- cheap cleanup, not a full HTML parse, since the only markup
    # Jooble actually emits in this field is these two things (confirmed by
    # inspecting real responses).
    text = TAG_RE.sub("", text or "")
    return text.replace("&nbsp;", " ").strip()

def fetch_jooble(retries=4, backoff=5):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(
                HOST + API_KEY,
                json=SEARCH_PARAMS,
                headers={"Content-type": "application/json"},
                timeout=(10, 30),
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            last_error = e
            print(f"  fetch attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(backoff * attempt)
    raise RuntimeError(f"Jooble unreachable after {retries} attempts") from last_error

def main():
    print(f"Searching Jooble for {SEARCH_PARAMS!r} (single page -- 500-request lifetime quota)...")
    data = fetch_jooble()
    jobs = data.get("jobs", [])
    print(f"Found {len(jobs)} offers (totalCount reported by Jooble: {data.get('totalCount')})")

    for j in jobs:
        j["snippet"] = clean_snippet(j.get("snippet"))

    os.makedirs("data/offers", exist_ok=True)
    with open("data/offers/raw_offers.json", "w") as f:
        json.dump({
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "search_params": SEARCH_PARAMS,
            "total_count_reported": data.get("totalCount"),
            "offers": jobs,
        }, f, indent=2, ensure_ascii=False)
    print("Wrote data/offers/raw_offers.json")
    if jobs:
        print("First offer preview:", json.dumps(jobs[0], ensure_ascii=False, indent=2)[:800])

if __name__ == "__main__":
    main()
