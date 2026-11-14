# Smart Internship Match — report

*I didn't have `project1_internship_job_search.md` (the formal brief) available locally
when writing this, so it's structured around the student manual's own stages and final
checklist instead. If the brief's section headers differ, the content below should map
onto them directly.*

## 1. Acquisition & provenance (CM3)

**France Travail was the intended primary source but was never actually usable.**
Registration and app creation on francetravail.io succeeded, but the "Offres d'emploi v2"
API never appeared in "Ajouter une API," and a direct OAuth2 token request with the
real issued Client ID/Secret returned `invalid_client` — confirmed by running the exact
`curl` request the manual's own `get_access_token()` makes. This is a real, concrete
acquisition failure, not a guess: the scope was simply never granted on this application.

**Jooble replaced it as the sole, primary source** (instructor-suggested, real issued
key). Tested directly before writing any pipeline code: a real search for
`"stage informatique"` in `"France"` returned 83,077 total matches and 30 real postings
(Thales, ArianeGroup, S3NS, BPCE...), confirmed working with no auth flow beyond the key
itself.

Two honest limits of this source, stated here and on the dashboard itself, not hidden:

1. **500-request lifetime quota**, not per-day. `fetch_offers_jooble.py` fetches exactly
   one page per run for this reason — no pagination loop, ever.
2. **Jooble pre-truncates its own snippet** to ~300 characters before this pipeline ever
   sees it. France Travail would have given the full posting text. This single fact
   explains most of what follows below.

`jobspy` (the manual's optional second source, Step 11b) was deliberately skipped:
Jooble is already an officially authorized source, so there was no reason to take on
`jobspy`'s real ToS-violation exposure just to get a second source.

## 2. KPI design — `score_offer()` (CM2)

This is the one real design task in the pipeline. Two real, observed problems in this
project's own data shaped the design — not hypothetical edge cases:

- **Case variants across offers**, confirmed in the real extraction run:
  `"Python"` / `"python"`, `"JAVA"` / `"Java"`, `"Informatique"` / `"informatique"`.
  Fixed by normalizing to lowercase before any comparison.
- **Vague, multi-word "skills"** caused by Jooble's truncated snippets — e.g. the model
  extracted `"développeur web"` (a job function) as if it were a tool, for one offer
  where the snippet simply didn't contain enough real content. A pure exact match would
  under-match almost everything on this data, so a second pass allows a whole-token
  substring match between a profile skill and an extracted one — but **only when both
  strings are ≥4 characters**, specifically to stop a short token like `"IA"`
  false-matching inside an unrelated word that happens to contain those two letters
  (e.g. `"diagnostic"`).

**The score itself is two-factor:** `0.6 × coverage + 0.4 × (average self-assessed level
of matched skills ÷ 5)`. A offer where I match 100% of stated skills, all at level 2/5,
should not automatically outrank one where I match 80% at level 5/5 — that's a real
judgment call about what "a good match" means for me specifically, not a neutral
formula. `matched`/`gaps` are returned using canonical (profile) casing specifically so
the cross-offer aggregation in `build_output()` doesn't re-fragment the same
case-variant problem one level up.

**Real result, sanity-checked by eye:** the #1-ranked offer (score 0.920) is a Python
automation/API internship — genuinely the kind of offer this profile should rank
highest. 24 of 30 offers scored exactly 0.0, almost all because of empty or
unmatchable `required_skills` — a real finding about this data source's quality, not a
bug in the scoring logic (confirmed by inspecting several 0.0 offers directly: their
`required_skills` were empty or contained only a vague domain word).

## 3. A real AI error caught (CM5, human-in-the-loop)

Checked `data/offers/structured_offers.json` directly, not just trusted it. Found:

> `"STAGE - Ingénieur développement IHM Web - F/H"` extracted `required_skills: ["Bac+5"]`
> and `experience_required: null`.

This is a genuine misclassification: the extraction prompt explicitly gives `"Bac+5"`
as an example of what belongs in `experience_required`, and the model still put it into
`required_skills` instead — exactly the kind of result a dashboard built on blind trust
of the LLM's output would have silently absorbed as a "skill gap." It shows up on the
real dashboard's "top skill gaps" chart as `"informatique"` (count 6) for the same
underlying reason — a generic domain word, not a real missing skill — which is why the
dashboard's assumptions box calls this out explicitly rather than hiding it.

**The three drafted cover-letter paragraphs** (`output/cv_drafts/`, reviewed) did
**not** show fabrication: each one only cited skills and evidence genuinely present in
`my_skills.csv` (e.g. the Java paragraph cites real Jakarta EE coursework, not invented
professional experience). Worth documenting as a real check performed, even though it
passed.

## 4. Privacy & publishability (CM6)

`docs/data/matches.json` and `docs/data/outcomes.json` are the only files ever
committed. Checked directly: neither contains the original posting URL's underlying
company-identifying detail beyond what's already public (title, company, a truncated
snippet-derived skill list), and `outcomes.json` is a pure aggregate — no row-level
application notes, dates, or company-specific outcome detail, which stay in the
gitignored `data/applications/tracker.csv` (filled in by hand, never AI-written, per
CM5). `.env`, every local-only intermediate (`merged_offers.json`,
`structured_offers.json`, `matches_all_local.json`), and `output/cv_drafts/` never
leave this machine.

## 5. Dashboard — chart choices argued (CM1)

Full argument for each chart is on the dashboard page itself (`docs/index.html`), next
to the chart it belongs to — summarized here:

- **Pipeline health → KPI cards only, no chart.** With one source and one run, there's
  no second category to compare against yet; a chart would have nothing real to show.
- **Match-score distribution → histogram (bar chart).** The real decision is "is this
  search producing real candidates or mostly noise" — a histogram shows the shape
  (heavily skewed toward 0, confirmed) at a glance, which 30 individual numbers
  wouldn't.
- **Top skill gaps / top matched strengths → two ranked bars, not one chart.** "What to
  learn next" and "what to lead with" are different, actionable questions, so each gets
  its own ranking — same logic as this course's other "ranking → bar chart" decisions.
- **Response rate by score bracket → bar chart, discrete brackets.** This is the KPI the
  brief explicitly asks for beyond "more applications, faster": does the scoring
  formula itself actually predict anything real? With zero tracked applications so far,
  the dashboard shows an honest "not enough data yet" message instead of an empty or
  misleading all-zero chart — a direct lesson carried over from a real empty-dashboard
  problem hit earlier in this course (TD2).

## 6. Monitoring (CM4, Stage 6)

**My design decision:** a green "Fetch succeeded" checkmark in the Actions tab doesn't
mean the search is actually producing anything worth acting on. `check_monitoring.py`
flags when **no offer has scored ≥0.6 for 7+ days**, even while the pipeline keeps
running successfully — the quiet failure mode a status check wouldn't catch on its own.

**Run twice, for real:** both runs on 2026-11-14 reported `OK` (4 offers currently
score ≥0.6, so nothing to flag yet). To confirm the alert path itself actually works
(not just the happy path), I separately ran the same script against a scratch copy of
the data with all high-scoring offers removed and the recorded "last good" timestamp
backdated 10 days — it correctly fired:

> `ALERT: No offer scoring >= 0.6 for 10 days (last one was on 2026-11-04)...`

This simulated run is documented here for transparency, not counted as one of the two
required real runs.

## 7. What's still open

- **GitHub repo, Secrets, Pages** not yet created — same manual sign-off step as every
  other project this term.
- **`data/applications/tracker.csv`** is currently empty (template only) — the outcome
  chart and the "response rate by score bracket" KPI will only become real once actual
  applications are sent and logged by hand.
- **France Travail access**: if it gets resolved later, it could be reintroduced as a
  genuine second official source (replacing `jobspy`'s slot), giving this pipeline a
  real multi-source acquisition stage it currently lacks.
