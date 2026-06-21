# Audience personas for Q&A drills

How to ask questions *in persona* so the drill feels like a real session
instead of a quiz. `scripts/qa_drill.py` picks the lineup and quotas; this
file is how each persona actually behaves.

## Contents

- [Ground rules for asking in persona](#ground-rules-for-asking-in-persona)
- [The persona catalog](#the-persona-catalog)
- [Venue-family calibration](#venue-family-calibration)
- [Setting calibration](#setting-calibration)

## Ground rules for asking in persona

1. **One question at a time, then wait.** Never dump a question list. The
   drill's value is the user formulating an answer under pressure; a list
   lets them read ahead and rehearse nothing.
2. **Stay in character for the follow-up.** A hostile persona is not
   satisfied by a deflection — push back once, the way a real questioner
   with a microphone would. Then break character to coach.
3. **Ground every question in the actual paper/slides.** Quote the claim,
   table, or slide the question attacks. Generic questions train nothing.
4. **The prior-work rule (non-negotiable).** When a persona invokes prior
   work ("didn't X et al. do this in 2019?"), the cited paper must be REAL
   and verified via `find-papers` + `verify-citations` — or the question
   stays nameless: "suppose someone claims a 2019 systems paper already did
   this — how do you respond?" Never invent an author, title, or year. A
   fabricated citation in a drill becomes a fabricated citation in the
   user's head at the podium.
5. **Realistic phrasing.** Real questions are spoken: slightly too long,
   sometimes with a wrong premise, occasionally rude. Mimic that — it is
   exactly what the user must learn to parse live.

## The persona catalog

For each persona: what they want, how they sound, and what the coached
answer must do. Question quotas come from `qa_drill.py`.

### The Hostile Skeptic (`hostile-skeptic`) — hostile

Reviewer 2 with a microphone. Believes the headline claim is oversold and
wants the room to know. Sounds like: "Isn't this just...", "I don't buy...".
Attacks the gap between what was claimed and what was shown.
**Coached answer:** concede the true scope in the first sentence, then
defend the contribution inside that scope with the paper's own evidence.
Never argue, never get louder.

### The Methods Stickler (`methods-stickler`) — hostile

Wants the experimental hygiene: baseline tuning budgets, seeds, splits,
hardware, dataset versions. Asks short factual questions and follows up if
the answer is vague.
**Coached answer:** exact numbers from memory. The drill should expose
which numbers the user does NOT know cold — those go on a crib sheet.

### The Statistician (`statistician`) — hostile

Significance tests, error bars, multiple comparisons, power. Quietly
devastating: "Is that difference within the error bars?"
**Coached answer:** name the test and the effect size, or say "single run,
agreed that limits the claim" — honestly and without collapsing.

### The Theory Prober (`theorist`) — hostile

Lives on assumptions and failure boundaries: "what breaks when X fails?",
"is the bound tight?". Common at ML and algorithms venues.
**Coached answer:** state assumptions crisply; know one concrete failure
case; keep "proved" and "observed empirically" rigorously separate.

### The Adjacent-Field Expert (`adjacent-expert`) — hostile

Knows a neighboring literature better than the speaker. The novelty
torpedo: "this looks equivalent to <real verified work / a classic
technique in field Y>". Subject to the prior-work rule above.
**Coached answer:** the rehearsed one-sentence delta versus the closest
prior work. If the user does not know the referenced area: "I don't know
that line of work well enough to compare on the spot — I'd love the
pointer" beats bluffing, every time.

### The Big-Picture Senior (`big-picture`) — curious

Asks why it matters and where it goes. Often the most senior person in the
room; the answer is a hiring signal.
**Coached answer:** a 30-second vision statement that starts with the
takeaway, not a recap of the method.

### The Confused Newcomer (`newcomer`) — curious

Honestly lost, asks the "dumb" question half the room is too embarrassed
to ask. Tests whether the user can drop ALL jargon.
**Coached answer:** plain language, one concrete example, zero
condescension. If the user cannot do this in 60 seconds, the talk's first
two minutes need rewriting (route to `write-talk-script`).

### The Industry Practitioner (`practitioner`) — curious

Cost, latency, scale, integration, licensing. "Would this survive
production?"
**Coached answer:** honest numbers where they exist, honest "untested
beyond N" where they don't; never let a research prototype be mistaken for
a product.

### The Reproducibility Auditor (`reproducibility-auditor`) — curious

"Can I reproduce Table 3 tonight?" Knows the difference between "code
available" and "code that runs".
**Coached answer:** exact artifact status — what is released, what is not,
and why — with no over-promising the user will regret in an email thread
next month.

### The Ethics Prober (`ethicist`) — hostile

Harms, consent, IRB, dual use, affected populations. Default at CHI-style
venues; increasingly common everywhere.
**Coached answer:** engage seriously, name the concrete mitigation, never
deflect with humor. "We didn't consider that" + a thoughtful 20 seconds
beats a canned dodge.

### The Self-Promoter (`self-promoter`) — curveball

"This is more of a comment, really..." Three sentences about their own
work, no question mark. The drill trains the redirect, not the content.
**Coached answer:** 20–30 seconds total — find the one answerable kernel,
answer it, then: "I'd love to compare notes after the session." Never
debate their work from the podium.

### The Rambler (`rambler`) — curveball

A three-part question with a flawed premise buried in part two. Tests
working memory and composure.
**Coached answer:** decompose out loud ("I count three questions"), answer
the most important first, correct the premise politely ("on the second —
small correction first..."), offer to take the rest offline if the chair
signals time.

## Venue-family calibration

`qa_drill.py` keys lineups on the `family:` field of the venue profile.
What actually differs:

| Family | Audience culture | Heaviest personas |
|---|---|---|
| `neurips-style` | theory + stats heavy; novelty-allergic; "did you compare to..." | theorist, statistician, adjacent-expert |
| `acm-sigconf` / `ieee-conf` | systems culture; scalability and baselines; "does it run at scale?" | methods-stickler, practitioner, reproducibility-auditor |
| `acm-manuscript-chi` | methods + ethics + generalizability; "who was in your sample?" | ethicist, methods-stickler |
| `lncs` | correctness and placement against the venue's own recent proceedings | methods-stickler, adjacent-expert |
| journals (`ieee-journal`, `acm-journal`) | no talks — use the `defense` or `job-talk` setting if rehearsing a related presentation | — |

Profiles never store talk-slot facts. Re-verify slot length, Q&A minutes,
and session format against the venue's live presenter instructions
(start from `cfp_url` / `website`) before rehearsing to the clock.

## Setting calibration

| Setting | What changes in the drill |
|---|---|
| `conference-talk` | 2–4 questions total live; chair cuts off; train SHORT answers (45s aim) |
| `lightning` | often no live Q&A at all (verify!); train the hallway/poster version instead |
| `keynote` | opinion and vision questions dominate; longer answers acceptable |
| `poster` | continuous; same questions dozens of times; also rehearse 2-min and 5-min pitches |
| `defense` | committee chains 2–3 follow-ups per topic; depth beats speed; "I don't know" must be followed by how you would find out |
| `job-talk` | interruptions mid-talk are normal; after each answer, rehearse the re-entry line back into the deck |
