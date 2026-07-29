# DeepSeek Repair Evaluation

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
