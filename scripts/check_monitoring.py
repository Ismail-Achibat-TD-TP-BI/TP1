import json, os, time
from datetime import datetime, timezone

# Stage 6 monitoring check. Per the manual: "design this check yourself; it's a
# real decision about what 'something's wrong with my search' should look like
# for you specifically." My real decision: a weekly fetch that keeps returning
# zero offers scoring >= HIGH_SCORE_THRESHOLD, for more than STALE_DAYS, is the
# honest signal that the search has gone quiet -- not "the pipeline crashed"
# (a workflow failure already shows red in the Actions tab on its own), but the
# quieter, easy-to-miss failure: the pipeline keeps succeeding while producing
# nothing worth acting on. That's the actual CM4 point -- a green checkmark is
# not the same thing as "my search is working."

HIGH_SCORE_THRESHOLD = 0.6
STALE_DAYS = 7
STATE_PATH = "data/monitoring/last_check.json"
MATCHES_PATH = "data/offers/matches_all_local.json"

def main():
    with open(MATCHES_PATH) as f:
        matches = json.load(f)

    high_scoring = [o for o in matches["offers"] if o["score"] >= HIGH_SCORE_THRESHOLD]
    now = datetime.now(timezone.utc)

    prev = None
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            prev = json.load(f)

    alert = False
    message = ""
    if prev is not None:
        last_good = datetime.fromisoformat(prev["last_time_with_high_scores"].replace("Z", "+00:00")) \
            if prev.get("last_time_with_high_scores") else None
        days_since_good = (now - last_good).days if last_good else None
        if high_scoring:
            pass  # good: at least one high-scoring offer right now, nothing to flag
        elif days_since_good is not None and days_since_good >= STALE_DAYS:
            alert = True
            message = (f"No offer scoring >= {HIGH_SCORE_THRESHOLD} for {days_since_good} days "
                       f"(last one was on {last_good.date()}). Pipeline is running, but nothing "
                       f"worth acting on has come through -- worth widening the search keywords "
                       f"or re-checking the required_skills extraction quality.")
        else:
            message = f"No high-scoring offer right now, but within the {STALE_DAYS}-day grace window."
    else:
        message = "First run -- no prior state to compare against yet."

    state = {
        "checked_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_offers": len(matches["offers"]),
        "n_high_scoring": len(high_scoring),
        "last_time_with_high_scores": now.strftime("%Y-%m-%dT%H:%M:%SZ") if high_scoring
            else (prev.get("last_time_with_high_scores") if prev else None),
        "alert": alert,
        "message": message,
    }
    os.makedirs("data/monitoring", exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)

    print(f"Checked {len(matches['offers'])} offers, {len(high_scoring)} scoring >= {HIGH_SCORE_THRESHOLD}")
    print("ALERT:" if alert else "OK:", message)

if __name__ == "__main__":
    main()
