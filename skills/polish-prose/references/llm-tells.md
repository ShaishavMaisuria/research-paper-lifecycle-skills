# LLM-tell catalog: what fires, why it reads as generated, how to rewrite

Companion to `scripts/prose_lint.py`. Every entry below maps to a linter
check. The rule throughout: **density is the tell, not existence.** One
"leverage" in eight pages is a word choice; five per section is a register.
And a tell that is also a domain term is innocent — see
[False positives](#false-positives-and-domain-term-exceptions).

## Contents

- [How to use this catalog](#how-to-use-this-catalog)
- [Chatbot artifacts (RISK — delete on sight)](#chatbot-artifacts-risk--delete-on-sight)
- [Lexical tells](#lexical-tells)
- [Stock phrases and filler](#stock-phrases-and-filler)
- [Structural tells](#structural-tells)
- [Formatting tells](#formatting-tells)
- [False positives and domain-term exceptions](#false-positives-and-domain-term-exceptions)
- [Worked rewrites](#worked-rewrites)
- [What "fixed" means](#what-fixed-means)

## How to use this catalog

1. Run `python3 scripts/prose_lint.py main.tex` and open the findings next
   to this file.
2. For each finding, decide: domain term (keep), best word for the job
   (keep, sparingly), or register noise (rewrite with the pattern below).
3. Rewrite to say the same thing more plainly — never to say something
   different. If a rewrite changes what the sentence claims, back out.

## Chatbot artifacts (RISK — delete on sight)

These are not style problems; they are pasted assistant output left in the
manuscript. Several venues treat undisclosed LLM text as a desk-reject
trigger, and every reviewer recognizes them instantly.

| Artifact | Action |
|---|---|
| "As an AI (language) model..." | Delete the sentence; rewrite the point in the authors' voice |
| "Certainly! Here is..." / "Here is a revised version of..." | Delete — it is the assistant's preamble, not prose |
| "[insert X]" / "[INSERT CITATION]" | Fill with the real content. A citation placeholder routes through `verify-citations`; never invent a reference to fill a hole |
| "I hope this helps" / "Let me know if you..." | Delete |
| "knowledge cutoff" | Delete or rewrite as a dated factual statement with a source |

## Lexical tells

Single words that spike in LLM output. Rewrite patterns, not bans:

| Tell | Why it fires | Rewrite pattern |
|---|---|---|
| delve (into) | Near-absent in pre-2022 CS prose, everywhere after | "examine", "analyze", or just state what you did: "We measure..." |
| leverage (verb) | Business register; LLMs use it for plain "use" | "use", "exploit", "build on" |
| showcase | Marketing register | "show", "demonstrate", "report" |
| underscore | Editorial register | "show", "confirm"; or delete the sentence — it usually restates the previous one |
| boast | Marketing | "has", "provides" |
| unveil / embark | Press-release register | "present", "introduce" / "begin" |
| pivotal / crucial | Importance asserted, not shown | Show the consequence instead: "without X, Y fails because..." |
| multifaceted / holistic | Vague scope words | Name the actual facets/components |
| seamless(ly) | Marketing | State the measured property: "without manual reconfiguration" |
| groundbreaking / cutting-edge / game-changing | Self-praise; reviewers punish it | Delete; let the delta over baselines speak |
| ever-evolving | Empty temporal filler | Delete, or cite the specific recent change |
| significant(ly) | Reads as statistical claim | If you ran a test, report it (test, p-value); otherwise "substantial", "large", or the actual number |

## Stock phrases and filler

| Phrase | Rewrite |
|---|---|
| "It is worth noting that X" / "It is important to note that X" / "It should be noted that X" | "X." — note things by saying them. If X truly needs flagging: "Note that X" (sparingly) |
| "plays a crucial/vital/key role in X" | Say what it does in X: "determines", "bounds", "dominates" |
| "in the realm/landscape of X" | "in X" |
| "in today's ..." | Delete, or anchor to a fact: "since the release of X..." |
| "a wide range of" / "a myriad of" | "many", or count them |
| "stands as a testament to" | Delete; state the evidence |
| "paves the way for" | "enables", or name the concrete follow-on work |
| "sheds (new) light on" | "explains", "shows why" |
| "at the forefront of" | Delete; cite who/what specifically |
| "has garnered significant attention" | Cite the actual surge: "X papers in the last two years [refs]" — citations route through `verify-citations` |
| "In recent years, there has been..." | Start with the subject: "Trajectory volumes grew..." |
| "not only X but also Y" | Once per paper is fine. Repeated: "X and Y", or two sentences |
| "with that being said" / "at the end of the day" / "needless to say" | Delete |

## Structural tells

These fire on density thresholds (documented in `prose_lint.py`), not
single uses:

- **Connective stacking** (`connective-stacking`, `connective-density`):
  consecutive paragraphs opening Moreover / Furthermore / Additionally.
  Fix: delete the connective. If the paragraph then feels disconnected,
  the real problem is ordering — fix the order, not the glue. A paper
  needs far fewer explicit connectives than an LLM emits; section
  structure and topic sentences carry the logic.
- **Em-dash chains** (`emdash-density`): more than ~5 per 1000 words of
  interrupting—like this—asides. Keep the two or three that earn their
  place; recast the rest as commas, parentheses, or separate sentences.
- **"not only ... but also" repetition**: a balanced-correlative habit.
  State the two facts plainly.
- **Uniform paragraph rhythm** (`uniform-paragraphs`): every paragraph
  3-4 sentences, every sentence mid-length. Merge short related
  paragraphs; split the long ones; let one important sentence stand
  alone.
- **Vague openers** (`vague-opener`): "There is/are...", "It is..." —
  give the sentence its real subject ("Trajectory queries dominate the
  workload", not "There is a dominance of trajectory queries in...").
- **Rule-of-three everywhere**: "fast, scalable, and robust" three-item
  lists in every other sentence. Vary list lengths; cut items that add
  nothing.
- **Summary-restating closers**: paragraphs that end by restating their
  own first sentence ("Thus, caching is important."). Delete the closer.

## Formatting tells

Not linted (LaTeX-specific or visual), check by eye:

- Bold-faced **Term:** lists where running prose belongs (fine in a
  design-goals list; a tell when every paragraph is secretly a bullet).
- Title-Case Section Headings at venues whose template uses sentence case
  (check the family template; `preflight-check` catches the template
  side).
- Emoji, smart-quote/straight-quote mixing, or "1) ... 2) ... 3) ..."
  enumerations inside a single sentence repeated throughout.
- Every section ending with a one-sentence "transition paragraph"
  previewing the next section. One roadmap paragraph at the end of the
  introduction is the convention; per-section previews are filler.

## False positives and domain-term exceptions

Keep the term, silence the finding (and consider `--allow` or the
glossary) when the "tell" is the technical term:

- **leverage scores** (randomized numerical linear algebra) — never
  rewrite.
- **robust statistics / robustness** as the formal property — keep;
  "robust" as decoration ("a robust framework") — rewrite.
- **significant** in a sentence that reports an actual statistical test —
  keep, with the test stated.
- **embedding / attention / transformer / diffusion** etc. are obviously
  fine; lexicons only flag register words, but stay alert in passes —
  e.g. "harness" in energy-systems papers, "landscape" in loss-landscape
  papers, "tapestry" in weaving papers (it happens).
- Quoted material and related-work summaries of *others'* wording: never
  edit inside quotation marks; cited paraphrases may keep the source's
  vocabulary.

## Worked rewrites

Before/after pairs (synthetic, written for this repo):

> **Before:** In today's ever-evolving landscape of spatial data
> management, caching plays a crucial role in interactive analytics.
>
> **After:** Interactive spatial analytics is cache-bound: tile recomputation
> dominates end-to-end latency in our measurements (Section 5).

> **Before:** Moreover, it is worth noting that our approach not only
> reduces latency but also lowers memory use.
>
> **After:** Our approach reduces median latency by 38% and memory use by
> 25%.

> **Before:** A novel caching framework is proposed in this paper, which
> leverages workload skew to optimize tile placement.
>
> **After:** We propose a caching policy that exploits workload skew: tiles
> are scored by access recency and recomputation cost, so hot regions stay
> resident as users migrate.

Notice what did NOT change in any pair: the numbers, the mechanism, the
claim. If your rewrite reads better but says more (or less), it is wrong.

## What "fixed" means

Fixed means a knowledgeable reader hears a careful author, the claims match
the evidence, and the linter is quiet or every remaining finding was a
conscious keep. It does **not** mean "passes an AI detector" — detectors
are unreliable in both directions and gaming them is not this skill's
purpose. If the venue requires AI-use disclosure, disclosure stands no
matter how clean the prose is (see
[venue-register.md](venue-register.md)).
