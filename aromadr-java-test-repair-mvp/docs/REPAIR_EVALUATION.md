# DeepSeek Repair Evaluation

## Final 100-Candidate Result

The formal evaluation now contains exactly 100 strict-eligible candidates:
17 from `deepseek-v1`, 26 from `deepseek-v2`, and 57 from `deepseek-v3`.

| Metric | V1 | V2 | V3 | Combined |
| --- | ---: | ---: | ---: | ---: |
| Eligible candidates | 17 | 26 | 57 | 100 |
| Accepted | 15 | 24 | 46 | 85 |
| Success rate | 88.2% | 92.3% | 80.7% | 85.0% |
| First-attempt accepted | 10 | 17 | 28 | 55 |
| Feedback-retry accepted | 5 | 7 | 18 | 30 |
| AromaDr findings before | 175 | 82 | 227 | 484 |
| AromaDr findings after | 6 | 2 | 22 | 30 |
| Model calls | 24 | 35 | 87 | 146 |
| Recorded tokens | 225,978 | 253,810 | 1,358,268 | 1,838,056 |
| Estimated API cost (USD) | 0.13805637 | 0.15097848 | 0.70249373 | 0.99152858 |

Every candidate passed baseline eligibility before it was sent to DeepSeek.
Accepted proposals compiled, passed the existing Maven suite, and had zero
authoritative AromaDr findings. Rejected proposals were restored from their
snapshots. The “findings after” row measures each last proposal before rollback;
all 30 remaining findings belong to rejected proposals. The original DataTD
working trees remained unchanged.

The automated 85/100 result is the primary prespecified endpoint. It does not
establish full semantic equivalence. A risk-informed cross-version review of 12
accepted v3 diffs found six clean passes and six manual quality failures,
principally constant-true assertions or weakened checks. This ratio is not a
random-sample estimate. See `docs/SEMANTIC_REVIEW_V3.md`.

## V2 Extension and Combined Formal Result

An independent `deepseek-v2` extension screened the extracted DataTD corpus
and froze 26 additional strict-eligible candidates from 10 projects. The
requested total was 50, but only 26 new candidates passed clean baseline
compilation, tests, and AromaDr eligibility, giving an interim denominator of
43. The later advisor-guided v3 protocol extended the final denominator to
100.

| Metric | V1 | V2 extension | Combined |
| --- | ---: | ---: | ---: |
| Eligible candidates | 17 | 26 | 43 |
| Accepted | 15 | 24 | 39 |
| Success rate | 88.2% | 92.3% | 90.7% |
| First-attempt accepted | 10 | 17 | 27 |
| Feedback-retry accepted | 5 | 7 | 12 |
| AromaDr findings before | 175 | 82 | 257 |
| AromaDr findings after | 6 | 2 | 8 |
| Model calls | 24 | 35 | 59 |
| Recorded tokens | 225,978 | 253,810 | 479,788 |
| Estimated API cost (USD) | 0.13805637 | 0.15097848 | 0.28903485 |

The v2 batch had no compile or test regressions in its final proposals. Two
proposals retained one AromaDr finding each and were rolled back. Manual
semantic review of ten accepted v2 diffs found eight clean passes, two passes
with caution, and no manual quality failures. See
`docs/SEMANTIC_REVIEW_V2.md` and `docs/EVALUATION_PROTOCOL_V2.md`.

## Research Question

Can a goal-driven coding backend remove AromaDr findings from real DataTD Java
tests while preserving compilation and the existing Maven test suite?

## Frozen Protocol

The held-out run used `deepseek-v1`, frozen before API execution:

- DeepSeek V4 Pro with thinking enabled
- complete-file JSON replacement
- at most two repair attempts
- one non-thinking recovery for invalid JSON
- baseline and post-repair Maven `test-compile` plus `test`
- AromaDr-authoritative feedback and acceptance
- one authorized Java test file in an isolated project copy
- rejected or exceptional proposals rolled back
- shared USD 1.00 budget and resumable checkpoints

Candidates 1–10 were excluded because they were used during development.

## Primary Result

DeepSeek produced accepted repairs for 15 of 17 held-out candidates, an 88.2%
success rate over strictly eligible attempts.

- 10 succeeded on the first proposal.
- 5 required the feedback proposal.
- 2 failed after the maximum of two proposals.
- No accepted repair left an AromaDr finding.
- No original DataTD source file changed.

## Smell Coverage

The frozen cohort contained these original smell categories:

| Smell | Candidate attempts | Accepted | Success |
| --- | ---: | ---: | ---: |
| AssertionRoulette | 5 | 5 | 100% |
| ConditionalTest | 1 | 1 | 100% |
| MagicNumberTest | 1 | 1 | 100% |
| UnknownTest | 13 | 11 | 84.6% |

Categories overlap because one test may contain multiple smells. Initial counts
were 116 AssertionRoulette, 1 ConditionalTest, 20 MagicNumberTest, and 38
UnknownTest findings.

## Cost and Runtime

- Model calls: 24
- Total tokens: 225,978
- Cache-aware estimated cost: USD 0.1381
- Aggregate candidate runtime: about 36.6 minutes
- Formal budget cap: USD 1.00

Runtime includes isolated project copies, Maven compilation/tests, AromaDr, and
model calls. The outer command exceeded a 30-minute tool window, but checkpoint
resume prevented repetition of completed candidates.

## Interpretation

The result supports the feasibility of an agentic smell-repair loop on real
Java tests. The strongest evidence is not smell reduction alone: every accepted
proposal also compiled and passed the project's existing tests. Feedback
iteration materially contributed, accounting for five accepted repairs.

The evidence does not prove full semantic equivalence. Existing tests may not
detect weakened intent, and AromaDr is a structural smell detector rather than
a behavioral oracle. Manual review of ten accepted repairs found seven clean
passes, one pass with a minor overconstraint caution, and two manual quality
failures: constant-true assertions and a duplicated slow integration flow.
These do not change the prespecified automated 15/17 result, but they show that
a stricter semantic quality gate is needed. See `docs/SEMANTIC_REVIEW.md`.

## Artifacts

- `docs/results/heldout_summary.json`
- `docs/results/heldout_candidates.csv`
- `docs/results/heldout_smell_types.csv`
- `docs/EVALUATION_PROTOCOL.md`
- local raw run: `.mvp_runs/heldout-evaluation-deepseek-v1`
- infrastructure rerun: `.mvp_runs/heldout-evaluation-rerun-013`
