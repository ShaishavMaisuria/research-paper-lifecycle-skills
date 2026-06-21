# Answer coaching

How to coach each answer during the drill: the structure good answers
share, the feedback loop after every exchange, and the playbook for the
situations that derail speakers.

## Contents

- [The answer-first template](#the-answer-first-template)
- [Timing discipline](#timing-discipline)
- [The coaching loop (after every answer)](#the-coaching-loop-after-every-answer)
- [Situation playbook](#situation-playbook)
- [Phrase bank](#phrase-bank)
- [Delivery notes](#delivery-notes)

## The answer-first template

Every coached answer has three beats, in this order:

1. **Headline (1 sentence).** The direct answer. For a yes/no question the
   first word is "yes", "no", "not yet", or "it depends — on X".
2. **Evidence (1–2 sentences).** The one number, experiment, or argument
   that supports the headline. From the paper, not improvised.
3. **Stop (optionally: bridge).** End cleanly. Optionally bridge once:
   "...and that's exactly why we ran the ablation in Table 4." Then stop
   talking. Trailing off invites the follow-up you don't want.

Anti-patterns to flag every time:

- **The wind-up:** 30 seconds of context before any answer appears.
  (`grade_answers.py` flags this as `buried-answer` on closed questions.)
- **The hedge opener:** "great question", "um, so basically", "I guess".
  Replace with a 1-second pause — silence reads as thought, filler reads
  as panic.
- **The second answer:** answering well, then answering again, worse.
  The first stop was correct.
- **Answering a better question:** responding to the question they wish
  had been asked. Politicians get away with it; speakers at a venue full
  of reviewers do not.

## Timing discipline

- Targets come from the drill plan (`qa_drill.py`): conference talks aim
  45s / cap 75s; defenses aim 90s / cap 180s; rapid-fire rounds cap 30s
  regardless of setting.
- A 3-minute conference Q&A fits ~2 live questions. Every 90-second answer
  costs the speaker one question — usually the friendly one they wanted.
- Coach the *stop*, not just the length: drill ending on a declarative
  sentence. "...so the gain survives at half the data. " — done.
- Grade typed/transcribed answers deterministically:
  `python3 scripts/grade_answers.py transcript.md --target 45 --max 75`.

## The coaching loop (after every answer)

After each user answer, break persona and give feedback in exactly this
shape — then move to the next question:

1. **Verdict in one line.** "Lands" / "too long" / "buried the answer" /
   "defensive tone".
2. **What worked.** One specific thing to keep (a number cited from
   memory, a clean concession, a good stop).
3. **The one fix.** Single highest-leverage change — never a list of five.
   Structure first, then content, then delivery.
4. **Model answer.** A 2–3 sentence version in the answer-first template,
   built only from what the paper actually supports. Never put a claim in
   the user's mouth that the paper cannot back.
5. **Re-drill rule.** If the answer was a hard fail (buried, over cap,
   factually shaky), re-ask the same question — possibly reworded — later
   in the session. An answer is "drilled" only when it lands twice.

Keep score across the session: which personas the user handles well, which
question *topics* keep failing. Topics that fail twice go into the
dreaded-question inventory (see
[dreaded-questions.md](dreaded-questions.md)) with a pre-built answer.

## Situation playbook

**"I don't know."** The strongest move available when true. Coach the
three-part version: (a) say it plainly — "I don't know"; (b) add the
nearest thing you DO know — "what I can say is that on the datasets we
tried, X held"; (c) for defenses, add how you'd find out. Never bluff: the
asker often knows the answer and asked to test honesty.

**The hostile question.** Acknowledge the valid core, reframe, answer:
"You're right that we only tested up to 10M records — beyond that is open.
Within that range, the speedup is consistent across all three datasets."
Do not match the asker's tone; the room sides with whoever stays calm.
Never concede a falsehood just to de-escalate.

**The wrong-premise question.** Correct the premise politely BEFORE
answering, or the correction is lost: "Small correction first — we don't
retrain per city; the model is shared. Given that, the answer is..."

**The multi-part question.** Decompose out loud: "I count three questions.
Taking the most important first..." Answer 1–2, offer the rest offline.
Chairs love speakers who do this; it shows control.

**The comment-not-question.** (Self-promoter.) Extract the one answerable
kernel, answer it in ~20 seconds, redirect: "I'd love to compare notes
after the session." Never debate a questioner's own work from the podium.

**The question you can't parse.** Ask for one clarification — once:
"Do you mean robustness to noise, or to distribution shift?" If still
unparseable, answer the most plausible reading and name it: "If the
question is about noise, then..."

**The question answered in the talk.** Never "as I said". Re-answer in one
fresh sentence — the asker missed it, and half the room did too.

**The chair signals time.** Headline-only answer (one sentence) plus
"happy to go deeper at the poster/by email." Practice compressing a
drilled 60-second answer into 10 seconds.

**The genuinely out-of-scope question.** "That's outside what we studied —
I'd be speculating. What we did measure is..." Speculation clearly labeled
as speculation is acceptable for vision questions; unlabeled speculation
is how misquotes are born.

## Phrase bank

Openers (replace hedges):
- "Yes — with one caveat: ..."
- "No, and the reason is ..."
- "It depends on one thing: ..."
- "Short answer: ..."
- "We tested exactly that — Table 3: ..."

Concessions that don't collapse:
- "That's a real limitation. Here's what survives it: ..."
- "Agreed — that's why we scoped the claim to X."
- "We haven't run that; my expectation, based on the ablation, is ..."

Deferrals (the parking lot):
- "I want to give that a real answer — can we take it offline?"
- "That deserves more than 30 seconds — find me at the poster."

Re-entry lines (job talks, after an interruption):
- "Great — and that connects to the next slide, where ..."
- "Hold that thought; slide 14 answers it directly — let me get there."

## Delivery notes

- **Repeat or paraphrase the question** when there's no audience mic: the
  room hears it, the recording captures it, and you buy three seconds.
- **Pause beats filler.** Train one beat of silence before the headline.
- **Look at the room, not only the asker** — the answer is for everyone.
- **Non-native speakers:** pre-script and memorize the *first sentence* of
  the top-10 dreaded answers verbatim; fluency under pressure comes from
  the memorized headline, after which evidence flows.
- **Write down post-session follow-ups** ("I'll email you that number")
  immediately — keeping those promises is networking that compounds.
