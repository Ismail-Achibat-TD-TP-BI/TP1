import csv, json, os, time

def load_profile(path="data/profile/my_skills.csv"):
    profile = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            profile[row["skill"]] = {"level": int(row["level"]), "evidence": row["evidence"]}
    return profile

def _normalize(s):
    return s.strip().lower()

def score_offer(profile, required_skills):
    """My KPI design. Two real, confirmed problems in this project's own data shaped it,
    not hypothetical ones:

    1. The same skill comes back with different casing across offers ("Python" vs
       "python", "JAVA" vs "Java" -- both actually found in this project's own real
       extraction run). A naive exact-match would silently split one real match into
       two, exactly as the manual warns. Fixed by normalizing to lowercase before
       comparing, in both directions.

    2. Jooble's snippets are pre-truncated by Jooble itself (~300 chars, see
       fetch_offers_jooble.py), so the LLM sometimes extracts vague multi-word phrases
       ("developpeur web") instead of clean atomic tool names -- a real, observed
       effect of this source, not a defect in extract_offers.py. A pure exact match
       would under-match almost everything on this data. So a second pass tries a
       whole-token substring match (profile skill found inside the extracted phrase,
       or vice versa) -- but ONLY when both strings are at least 4 characters, to
       avoid a short abbreviation like "IA" false-matching inside an unrelated word
       that happens to contain those two letters (e.g. "diagnostic").

    Score itself is two-factor, not a single count: how much of the offer I cover
    (coverage), combined with how strong I actually am in what I cover (my own
    self-assessed level on the matched skills). A 100%-covered offer in skills I rated
    myself 2/5 on should not outscore an 80%-covered offer in skills I rated 5/5 on --
    that's a real, deliberate judgment call (CM2: a KPI is a construct), not a neutral
    formula. Weighted 60% coverage / 40% level: coverage is what actually determines
    whether I can credibly apply at all, level is the secondary tiebreaker.

    matched/gaps are returned using canonical, deduplicated casing specifically so
    build_output()'s cross-offer aggregation (top_skill_gaps/top_matched_skills)
    doesn't re-fragment the same case-variant problem one level up.
    """
    profile_lookup = {_normalize(k): k for k in profile}

    distinct_required = []
    seen = set()
    for raw in required_skills:
        norm = _normalize(raw)
        if norm and norm not in seen:
            seen.add(norm)
            distinct_required.append(norm)

    if not distinct_required:
        return {"score": 0.0, "coverage": 0.0, "matched": [], "gaps": []}

    matched, gaps = [], []
    for norm in distinct_required:
        canonical = profile_lookup.get(norm)
        if canonical is None:
            for p_norm, p_canonical in profile_lookup.items():
                if len(p_norm) >= 4 and len(norm) >= 4 and (p_norm in norm or norm in p_norm):
                    canonical = p_canonical
                    break
        if canonical:
            matched.append(canonical)
        else:
            gaps.append(norm)

    matched = sorted(set(matched))
    gaps = sorted(set(gaps))
    coverage = len(matched) / len(distinct_required)
    avg_level = (sum(profile[s]["level"] for s in matched) / len(matched) / 5) if matched else 0.0
    score = round(0.6 * coverage + 0.4 * avg_level, 3)
    return {"score": score, "coverage": round(coverage, 3), "matched": matched, "gaps": gaps}

def build_output(results, profile):
    gap_counts = {}
    matched_counts = {}
    for r in results:
        for g in r["gaps"]:
            gap_counts[g] = gap_counts.get(g, 0) + 1
        for s in r["matched"]:
            matched_counts[s] = matched_counts.get(s, 0) + 1
    top_gaps = sorted(gap_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    top_matched = sorted(matched_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    n_with_comp = sum(1 for r in results if r.get("compensation_mentioned"))
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_offers": len(results),
        "offers": results,
        "top_skill_gaps": [{"skill": s, "count": c} for s, c in top_gaps],
        "top_matched_skills": [{"skill": s, "count": c, "level": profile[s]["level"]} for s, c in top_matched],
        "n_offers_with_compensation": n_with_comp,
    }

def main():
    profile = load_profile()
    with open("data/offers/structured_offers.json") as f:
        data = json.load(f)

    results = []
    for offer in data["offers"]:
        m = score_offer(profile, offer["required_skills"])
        results.append({**offer, **m})

    results.sort(key=lambda r: r["score"], reverse=True)
    for r in results:
        print(f"  {r['score']:.3f}  {r['title']} @ {r['company']}  ({r['source']}, "
              f"coverage {r['coverage']:.0%}, gaps: {r['gaps']})")

    os.makedirs("data/offers", exist_ok=True)
    with open("data/offers/matches_all_local.json", "w") as f:
        json.dump(build_output(results, profile), f, indent=2, ensure_ascii=False)
    print(f"Wrote data/offers/matches_all_local.json ({len(results)} offers) -- gitignored, local only")

    public_results = [r for r in results if r.get("publishable", False)]
    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/matches.json", "w") as f:
        json.dump(build_output(public_results, profile), f, indent=2, ensure_ascii=False)
    print(f"Wrote docs/data/matches.json ({len(public_results)} of {len(results)} offers -- publishable sources only)")

if __name__ == "__main__":
    main()
