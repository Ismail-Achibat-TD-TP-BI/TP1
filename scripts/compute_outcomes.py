import csv, json, os, time
from datetime import date

# Outcome KPIs -- Stage 6/the brief's "outcome" category. The tracker itself
# (data/applications/tracker.csv) is a plain table YOU fill in by hand as you
# actually apply -- never written to by an AI, per CM5's human-in-the-loop
# principle. This script only ever reads it and aggregates; it never invents
# a row. Only the aggregate (counts/rates, no row-level notes or company
# detail) is written to docs/data/outcomes.json -- the same
# publishable/local split this project uses everywhere else.

TRACKER_PATH = "data/applications/tracker.csv"
OUT_PATH = "docs/data/outcomes.json"

# Per the brief: "at least one KPI that isn't just more applications, faster."
# This is that one -- response rate BY match-score bracket, not just overall --
# answers a genuinely different question: does this project's own score
# actually predict anything real, or is it just a number?
SCORE_BRACKETS = [(0.0, 0.3), (0.3, 0.6), (0.6, 1.01)]

def load_tracker():
    if not os.path.exists(TRACKER_PATH):
        return []
    # The tracker is hand-edited in whatever editor/encoding the user has --
    # real observed case: saved as ISO-8859-1 (Latin-1) by the editor, not
    # UTF-8, which crashes a plain utf-8 open() the moment an accented
    # character (e.g. "Developpeur", "Credit") appears. Try UTF-8 first,
    # fall back to Latin-1 rather than assuming the file is well-formed.
    try:
        with open(TRACKER_PATH, encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except UnicodeDecodeError:
        with open(TRACKER_PATH, encoding="latin-1") as f:
            return list(csv.DictReader(f))

def main():
    rows = load_tracker()
    n_tracked = len(rows)
    n_sent = sum(1 for r in rows if r.get("status") not in ("", "not_sent"))
    n_responded = sum(1 for r in rows if r.get("response_date"))

    bracket_stats = []
    for lo, hi in SCORE_BRACKETS:
        in_bracket = [r for r in rows if r.get("score") and lo <= float(r["score"]) < hi]
        sent_in_bracket = [r for r in in_bracket if r.get("status") not in ("", "not_sent")]
        responded_in_bracket = [r for r in sent_in_bracket if r.get("response_date")]
        bracket_stats.append({
            "score_range": f"{lo:.1f}-{hi if hi <= 1 else 1.0:.1f}",
            "n_applied": len(sent_in_bracket),
            "n_responded": len(responded_in_bracket),
            "response_rate": round(len(responded_in_bracket) / len(sent_in_bracket), 3) if sent_in_bracket else None,
        })

    output = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_offers_tracked": n_tracked,
        "n_applications_sent": n_sent,
        "n_responses": n_responded,
        "overall_response_rate": round(n_responded / n_sent, 3) if n_sent else None,
        "response_rate_by_score_bracket": bracket_stats,
        "note": "Empty/null values mean no applications have been tracked yet -- "
                "this is an honest 'no data', not a zero, since the tracker "
                "(data/applications/tracker.csv) is filled in by hand as the real "
                "search progresses, not generated.",
    }
    os.makedirs("docs/data", exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(json.dumps(output, indent=2))
    print(f"\nWrote {OUT_PATH}")

if __name__ == "__main__":
    main()
