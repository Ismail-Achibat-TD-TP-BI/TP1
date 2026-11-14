import json, os

# This project uses Jooble as its sole, primary source (see fetch_offers_jooble.py
# for why: France Travail's "Offres d'emploi v2" scope was never granted on this
# course's francetravail.io application -- a real token request returned
# invalid_client, not a hypothetical problem). The optional jobspy second-source
# path (manual Step 11b) is deliberately skipped: Jooble is already an officially
# authorized source with a real issued key, so there's no need to take on jobspy's
# ToS-violation risk just to get a second source. This file still exists, in the
# same shape the manual gives every other project, so a second source could be
# added later without changing anything downstream.

RAW_JOOBLE_PATH = "data/offers/raw_offers.json"
MERGED_PATH = "data/offers/merged_offers.json"

def normalize_jooble(raw_offers):
    normalized = []
    for o in raw_offers:
        normalized.append({
            "id": f"jooble_{o['id']}",
            "source": "jooble",
            "origin_site": o.get("source"),  # the underlying site Jooble aggregated this from (e.g. "hellowork.com")
            "title": o.get("title"),
            "company": o.get("company"),
            "location": o.get("location"),
            "description": o.get("snippet", ""),
            "url": o.get("link"),
            "date_posted": o.get("updated"),
            "offer_type": o.get("type"),  # sometimes literally "Stage" -- Jooble's own type field
            "is_apprenticeship": False,  # Jooble doesn't expose this as a structured field
            "accessible_disability": False,  # neither does this
            "publishable": True,  # officially authorized source (a real issued API key) -- safe to publish
        })
    return normalized

def main():
    with open(RAW_JOOBLE_PATH) as f:
        raw = json.load(f)
    merged = normalize_jooble(raw["offers"])
    print(f"Normalized {len(merged)} Jooble offers")

    os.makedirs("data/offers", exist_ok=True)
    with open(MERGED_PATH, "w") as f:
        json.dump({"offers": merged}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {MERGED_PATH} ({len(merged)} offers) -- gitignored, local only")

if __name__ == "__main__":
    main()
