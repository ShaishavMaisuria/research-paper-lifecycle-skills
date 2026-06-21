# Contribution reframing per track

How to reposition the SAME work for a different track or venue type. Track
choice changes what reviewers reward — reframing is rewriting the claim, not
the work.

## Contents

- [What each track rewards](#what-each-track-rewards)
- [The five reframing surfaces](#the-five-reframing-surfaces)
- [Track-by-track playbook](#track-by-track-playbook)
- [Cross-venue repositioning](#cross-venue-repositioning)
- [Red flags reviewers punish](#red-flags-reviewers-punish)

## What each track rewards

| Track | Reviewers reward | Reviewers punish |
|---|---|---|
| Research | novelty of technique, rigor, generality, strong baselines | "engineering effort" framing, no comparison to state of the art |
| Applications / Industry | real deployment, real data, scale, lessons learned, honest failure analysis | toy datasets dressed as applications, hiding operational pain |
| Demo | what an attendee can see and do in 5 minutes, system maturity | research claims with nothing interactive to show |
| Short / Poster | one crisp idea, early but credible evidence | a compressed full paper that lost its evaluation |
| Vision / Position | a defensible provocative argument, research agenda for others | incremental ideas inflated with futurist language |
| Experiment / Benchmark | reproducibility, fairness of comparison, surprising findings | new-method claims smuggled into a study paper |

## The five reframing surfaces

Work through these in order — they cascade:

1. **Title.** Signal the track. Applications: name the domain and deployment
   ("...for Fleet Routing at Nationwide Scale"). Demo: name the artifact and
   often prefix/suffix per CFP rules (SIGSPATIAL Experiment/Benchmark papers
   must carry an "[Experiment]" style suffix in the title — check the profile
   notes and CFP). Vision: pose the question or claim.
2. **Abstract.** Re-balance the motivation→gap→approach→results→impact arc:
   Research leads with the gap; Applications leads with the deployment context
   and measured operational impact; Demo leads with what the system does and
   what the audience experiences.
3. **Contributions list (end of intro).** Rewrite every bullet so its noun
   matches the track: Research bullets name techniques and theorems;
   Applications bullets name deployments, datasets, and lessons; Demo bullets
   name capabilities and the demonstration scenario.
4. **Evaluation emphasis.** Research: ablations + strongest baselines.
   Applications: longitudinal/production metrics, cost, failure modes.
   Demo: responsiveness, supported workflows, robustness during a live demo.
   Short: ONE convincing experiment, not four shallow ones.
5. **Related work framing.** Research positions against techniques.
   Applications positions against alternative practical solutions (including
   commercial ones and "do nothing"). Demo cites the research it showcases
   plus comparable systems/demos.

## Track-by-track playbook

### Research → Applications / Industry

- Promote deployment context from Section 6 to Section 1. Reviewers must see
  the real setting on page 1.
- Replace ablation depth with operational evidence: traffic volumes, uptime,
  integration cost, before/after business or scientific metrics.
- Add a "Lessons learned" section — frequently an explicit CFP requirement
  and the part industry reviewers actually read.
- Keep ONE technical-novelty subsection; cut the rest of the method detail or
  cite your own research paper if it is published (mind anonymization rules).
- Honesty sells: include what broke in production and what you would redo.

### Research → Demo

- This is a rewrite, not a cut. Typical demo budget is 4 pages INCLUDING
  references (check the profile track entry).
- Structure: (1) problem + system in one paragraph, (2) architecture, one
  figure, (3) **the demonstration scenario** — the walkthrough an attendee
  performs, step by step, (4) what makes it technically interesting, (5)
  screenshot/screencast figure.
- The demonstration scenario section is the acceptance criterion. Write it
  as a concrete narrative: "The attendee selects a city, injects a simulated
  GPS outage, and watches the index re-partition live."
- Mention hardware/connectivity needs if the CFP asks (booth, screen, VR).

### Research → Short / Poster

- Pick the single strongest claim; delete secondary contributions entirely
  (do not compress them — deleting reads better than cramming).
- One experiment with the best baseline; move everything else to an arXiv
  version or the next full submission.
- Intro shrinks to 2-3 paragraphs; related work to one paragraph of grouped
  citations.

### Research → Vision

- Lead with the argument, not the system. Your prototype becomes "early
  evidence", one section at most.
- Add a research-agenda section: enumerate open problems others could pick
  up — this is what vision-track reviewers score.

### Applications → Research

- The hard direction. You must add: a generalizable technique extracted from
  the system, ablations isolating it, and comparisons against published
  baselines — production anecdotes do not substitute.
- If the novelty is thin, target the Experiment/Benchmark or Industry track
  of a research venue instead — far better odds than a weak research paper.

## Cross-venue repositioning

When moving between venues (e.g. data-engineering venue → ML venue), also re-aim:

- **Vocabulary**: communities name the same concept differently; mirror the
  target venue's term (check 2-3 recent titles from the venue via the
  `find-papers` skill — do not guess).
- **Baseline set**: reviewers expect comparisons against THEIR community's
  systems. A missing community-standard baseline reads as ignorance.
- **Claim altitude**: ML venues reward generality; systems venues reward
  end-to-end wins; domain venues (e.g. GIS) reward domain fidelity.
- **Citation mix**: if fewer than ~25% of references are from the target
  community, reviewers infer the paper was written for somewhere else.
  Any NEW citations you add must go through the `verify-citations` skill.

## Red flags reviewers punish

- Track-mismatched evaluation (production metrics in a research track,
  ablations-only in an industry track).
- A contributions list untouched from the previous venue's submission —
  reviewers who saw the earlier version will notice.
- Claiming both novelty and deployment maturity equally; pick the lead claim.
- Forgetting venue-mandated sections after reframing (impact statements,
  AI-use acknowledgements, lessons-learned) — `venue_diff.py` flags the ones
  the profile knows about; the live CFP is authoritative.
