# Advisor Summary

## Outcome

The project now implements a complete Java test-smell repair prototype using
Maven, AromaDr, and DeepSeek V4 Pro.

Across three independently frozen protocols:

- Exactly 100 strictly eligible Java test files from 39 project/module IDs
  were evaluated.
- 85 passed compilation, the existing Maven tests, and the zero-finding
  AromaDr acceptance gate: 85.0%.
- 55 succeeded on the first proposal; 30 required feedback.
- 484 original AromaDr findings were present; last proposed versions retained
  30, all in rejected proposals.
- The runs used 146 model calls, 1,838,056 tokens, and about USD 0.992.
- All 15 failed proposals were rolled back.
- No original DataTD source file was modified.

## Important Qualification

The automated result is the prespecified primary endpoint, not a claim that all
85 repairs are semantically ideal. Manual reviews found limitations that Maven
and AromaDr cannot reliably detect, including constant-true assertions,
weakened behavioral checks, and timing-risk changes. In a v3 risk-informed
cross-version review, 6 of 12 accepted diffs passed cleanly and 6 failed the
stricter manual quality gate; this ratio is not a random-sample estimate.

Therefore, the defensible primary claim is:

> DeepSeek satisfied the automated compile/test/AromaDr gate on 85 of 100
> formally evaluated candidates (85.0%). Manual review still shows that
> semantic-quality checks remain necessary beyond structural smell removal.

## Scope and Limitations

- The 30 GB archive and advisor benchmark workbook were used for expanded
  discovery, but the experiment does not claim an exhaustive all-file run.
- The v3 cohort reconstructed exact benchmark commits from local Git objects
  and used the advisor-specified Java 8, 11, or 17 toolchain.
- The combined formal cohorts cover the AromaDr smell categories present in
  the eligible sample.
- Passing existing tests does not prove full semantic equivalence.
- One candidate required an infrastructure-only rerun after a timeout/resume race.
- JaCoCo and PIT would strengthen behavioral evaluation but are optional extensions.

## Deliverables

- Frozen protocol: `docs/EVALUATION_PROTOCOL.md`
- Extension protocol: `docs/EVALUATION_PROTOCOL_V2.md`
- 100-candidate extension protocol: `docs/EVALUATION_PROTOCOL_V3.md`
- Dataset result: `docs/DATATD_RESULTS.md`
- Repair evaluation: `docs/REPAIR_EVALUATION.md`
- Failure analysis: `docs/FAILURE_ANALYSIS.md`
- Manual review: `docs/SEMANTIC_REVIEW.md`
- Extension manual review: `docs/SEMANTIC_REVIEW_V2.md`
- V3 manual review: `docs/SEMANTIC_REVIEW_V3.md`
- Path-neutral data: `docs/results/`
