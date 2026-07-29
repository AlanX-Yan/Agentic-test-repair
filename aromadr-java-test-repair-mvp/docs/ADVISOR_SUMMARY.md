# Advisor Summary

## Outcome

The project now implements a complete Java test-smell repair prototype using
Maven, AromaDr, and DeepSeek V4 Pro.

In a frozen held-out DataTD sample:

- 17 strictly eligible Java test files were repaired.
- 15 passed compilation, the existing Maven tests, and AromaDr: 88.2%.
- 10 succeeded on the first proposal; 5 required feedback.
- 175 original AromaDr findings were present.
- Accepted repairs ended with zero AromaDr findings.
- The run used 24 model calls, 225,978 tokens, and about USD 0.138.
- Both failed proposals were rolled back.
- No original DataTD source file was modified.

## Important Qualification

Ten accepted diffs were manually reviewed. Eight were acceptable, including
one with a minor overconstraint caution. Two exposed limitations not caught by
Maven and AromaDr: meaningless constant-true assertions and duplication of a
slow test flow that increased timeout risk.

Therefore, the defensible primary claim is:

> DeepSeek satisfied the automated compile/test/AromaDr gate on 15 of 17
> held-out candidates, while manual review shows that semantic-quality checks
> remain necessary beyond structural smell removal.

## Scope and Limitations

- The experiment is a controlled sample from DataTD, not a full 30 GB scan.
- The held-out cohort covers four original AromaDr smell categories.
- Passing existing tests does not prove full semantic equivalence.
- One candidate required an infrastructure-only rerun after a timeout/resume race.
- JaCoCo and PIT would strengthen behavioral evaluation but are optional extensions.

## Deliverables

- Frozen protocol: `docs/EVALUATION_PROTOCOL.md`
- Dataset result: `docs/DATATD_RESULTS.md`
- Repair evaluation: `docs/REPAIR_EVALUATION.md`
- Failure analysis: `docs/FAILURE_ANALYSIS.md`
- Manual review: `docs/SEMANTIC_REVIEW.md`
- Path-neutral data: `docs/results/`
