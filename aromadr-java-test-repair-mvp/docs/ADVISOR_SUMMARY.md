# Advisor Summary

## Outcome

The project now implements a complete Java test-smell repair prototype using
Maven, AromaDr, and DeepSeek V4 Pro.

Across the original frozen evaluation and an independently frozen extension:

- 43 strictly eligible Java test files were repaired.
- 39 passed compilation, the existing Maven tests, and AromaDr: 90.7%.
- 27 succeeded on the first proposal; 12 required feedback.
- 257 original AromaDr findings were present; final proposals retained 8.
- The runs used 59 model calls, 479,788 tokens, and about USD 0.289.
- All four failed proposals were rolled back.
- No original DataTD source file was modified.

## Important Qualification

Ten accepted diffs were manually reviewed. Eight were acceptable, including
one with a minor overconstraint caution. Two exposed limitations not caught by
Maven and AromaDr: meaningless constant-true assertions and duplication of a
slow test flow that increased timeout risk.

Therefore, the defensible primary claim is:

> DeepSeek satisfied the automated compile/test/AromaDr gate on 39 of 43
> formally evaluated candidates (90.7%). Manual review still shows that
> semantic-quality checks remain necessary beyond structural smell removal.

## Scope and Limitations

- The 30 GB archive was used for expanded discovery, but not every Java test
  file was executed. Strict screening found only 26 new eligible candidates,
  so the requested total of 50 could not be reached without invalid rows.
- The combined formal cohorts cover the AromaDr smell categories present in
  the eligible sample.
- Passing existing tests does not prove full semantic equivalence.
- One candidate required an infrastructure-only rerun after a timeout/resume race.
- JaCoCo and PIT would strengthen behavioral evaluation but are optional extensions.

## Deliverables

- Frozen protocol: `docs/EVALUATION_PROTOCOL.md`
- Extension protocol: `docs/EVALUATION_PROTOCOL_V2.md`
- Dataset result: `docs/DATATD_RESULTS.md`
- Repair evaluation: `docs/REPAIR_EVALUATION.md`
- Failure analysis: `docs/FAILURE_ANALYSIS.md`
- Manual review: `docs/SEMANTIC_REVIEW.md`
- Extension manual review: `docs/SEMANTIC_REVIEW_V2.md`
- Path-neutral data: `docs/results/`
