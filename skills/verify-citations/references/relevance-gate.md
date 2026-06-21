# Relevance gate — telling good additions from off-topic ones

A citation can resolve perfectly and still not belong in the paper. When
references arrive *independently* of the draft — gathered by `literature-review`,
`draft-related-work`, a search tool, or a co-author dropping in "related work" —
resolution alone cannot tell a **good addition** (topically load-bearing) from
an **off-topic** one (real paper, wrong paper for this argument). The relevance
gate scores topical fit so low-fit additions get flagged for human review
instead of slipping in unexamined.

It is **opt-in** and **advisory**. It never removes a reference; it raises a
`LOW_RELEVANCE` WARN for the user to judge. It is also strictly
**non-fabricating**: every number comes from the script's deterministic scoring
or from an embedding model you actually ran — never from memory.

## Table of contents

1. [When to run it](#when-to-run-it)
2. [The two signals](#the-two-signals)
3. [Invocation](#invocation)
4. [The embedding upgrade (preferred when available)](#the-embedding-upgrade)
5. [Acting on LOW_RELEVANCE](#acting-on-low_relevance)
6. [Tuning and limits](#tuning-and-limits)

## When to run it

Run the gate when you cannot vouch for every reference by hand:

- another skill appended references and you need to triage them;
- a large `.bib` accumulated across co-authors and you suspect drift;
- you are about to submit and want a last pass for citations that wandered
  off-topic (a reviewer reading an off-topic citation assumes padding).

Skip it for a small, hand-curated bibliography you already trust — the gate is
for scale and for independently-gathered sets.

## The two signals

The gate combines two non-fabricating signals. Neither alone condemns a
reference; together they separate anchored from adrift.

1. **Topical fit to the paper's thesis.** How much of the reference's
   title/venue/keywords overlaps the paper's thesis or abstract. The bundled
   script uses a transparent lexical proxy (Jaccard overlap of content words
   after LaTeX-aware normalization) so it works with zero dependencies and is
   fully reproducible. This is a *proxy* — see [the embedding
   upgrade](#the-embedding-upgrade) for a stronger version.

2. **Co-citation density with the confirmed core set.** Given a set of
   references you have confirmed are core to the paper (`--core-key`), the gate
   checks whether each other reference sits in the same citation neighborhood:
   does a core paper's reference list also cite this entry? A reference the
   core set co-cites is topically anchored; one that shares no citation
   neighborhood is a candidate off-topic addition. Co-citation is corroborating
   — its *presence* rescues a low-lexical entry, but its *absence* alone never
   condemns one (many on-topic papers are simply newer than the core set).

An entry is flagged `LOW_RELEVANCE` only when it scores low on lexical fit
**and** is not co-cited by the core set. An entry that scores well on either
gets the informational `RELEVANCE_OK`.

## Invocation

```bash
# Thesis-only: lexical fit against the paper's thesis/abstract.
python3 scripts/check_bibtex.py refs.bib --thesis-file thesis.txt

# Add co-citation: name the references you have already confirmed are core.
python3 scripts/check_bibtex.py refs.bib \
    --thesis-file thesis.txt \
    --core-key dean2008mapreduce --core-key vaswani2017attention
```

`--thesis-file` is plain text — the abstract, the intro's thesis paragraph, or
a one-line statement of the paper's contribution all work. `--core-key` is
repeatable; pass the keys of the seed papers the work is built on. The gate is a
no-op unless at least one of the two is supplied, and it only scores entries
that resolved online (an unresolved entry's problem is resolution, not
relevance).

## The embedding upgrade

The script's lexical overlap is deliberately simple and dependency-free. When
you (the agent) have an embedding model available, compute a stronger signal
yourself and let it override the lexical proxy in your advice:

1. Take the paper's thesis/abstract and each candidate reference's
   title + abstract. (Fetch abstracts only transiently for scoring — per the
   skill's hard rules, do **not** store fetched abstracts in the repo.)
2. Embed both and take cosine similarity.
3. Combine with the script's co-citation signal: high co-citation density plus
   high embedding similarity = clearly on-topic; low on both = off-topic
   candidate to raise with the user.

Report which signal you used. Never invent a similarity number — if you did not
actually run a model, say you used the lexical proxy.

## Acting on LOW_RELEVANCE

`LOW_RELEVANCE` is a prompt for human judgment, not a verdict:

1. Show the user the entry and its score, framed as a question: "this addition
   scored low topical fit — is it load-bearing for your argument?"
2. If it is genuinely off-topic, the user removes it — and you also remove the
   `\cite` and adjust the surrounding prose (the same care as an UNRESOLVED
   removal).
3. If it is relevant but the gate missed it (a foundational paper whose title
   does not lexically resemble the thesis; a cross-disciplinary citation), keep
   it. False positives are expected and fine — the gate trades precision for
   not letting off-topic citations pass silently.
4. **Never auto-remove.** A wrongly dropped citation that breaks a claim is
   worse than an extra one a reviewer skims past.

## Tuning and limits

- Thresholds (`LEX_LOW`, `LEX_OK`) live at the top of `relevance_gate()` in the
  script and are intentionally conservative — better to under-flag than to
  pester the user about clearly-relevant entries.
- The lexical proxy is weak for very short titles and for venues/keywords the
  thesis does not name; co-citation and the embedding upgrade compensate.
- Co-citation depends on Crossref reference lists, which are present for most
  but not all DOIs. When Crossref is unreachable, the co-citation signal is
  recorded as skipped and the run downgrades to PARTIAL-PASS (see
  [triage-guide.md](triage-guide.md#the-partial-pass-verdict)).
- The gate is generic by construction: it hardcodes no venue, field, or paper —
  it reasons only from the thesis text and the core set you supply.
