# Failure Analysis

## Held-Out Repair Failures

Two of 17 held-out candidates were rejected after two model proposals. Both
were rolled back, and both original DataTD files remained unchanged.

### OrderServiceTest — Behavioral Regression

- Project: `codingthought-ddd-aggregate-helper`
- Original AromaDr findings: 3 `UnknownTest`
- Final proposal AromaDr findings: 0
- Compilation: passed
- Tests: failed, with two failures and one error

The proposal added assertions and eliminated the structural findings, but its
new expected values and reflection-based setup did not match actual behavior.
Examples included an expected order number that remained `null` and reflection
against a nonexistent `skuId` field. This is a model semantic-repair failure:
smell removal alone was insufficient, and the Maven test gate correctly
rejected it.

### MetricAnnotationAdvisorTest — Compilation Regression

- Project: `dm-drogeriemarkt-micrometer-metrics-wrapper`
- Original AromaDr findings: 4 `UnknownTest`
- Final compilation: failed
- Final authoritative findings observed on the invalid source: 5
  `ExceptionHandling` and 1 `DuplicateAssert`

The replacement source was not syntactically valid Java; Maven reported
top-level declaration errors beginning near the start of the file. The feedback
proposal did not recover within the two-attempt budget. The validator caught
package/class mismatches but did not parse Java syntax before Maven, so Maven
remained the authoritative syntax gate.

## Infrastructure Incident

The first 17-candidate command exceeded the outer tool's 30-minute execution
window after 12 checkpointed candidates. The original process continued
briefly, and an early resume attempt raced with its partially created task
directory. Candidate 13 received an inconsistent `baseline-recorded` terminal
artifact despite model calls.

Resolution:

- no prompt or model setting changed;
- the runner was fixed to remove only the exact uncheckpointed isolated task
  directory during resume;
- candidate 13 was rerun independently under the frozen protocol;
- the rerun was accepted and is used in adjusted aggregate results;
- the contaminated artifact remains available for audit.

## Baseline Ineligibility

Before held-out selection, candidates 11–40 produced:

- 30 screened
- 22 compiled
- 11 passed tests and were eligible
- 11 compiled but failed baseline tests
- 7 failed compilation
- 1 produced a baseline infrastructure error

Fifteen deterministic replacements were then screened:

- 11 compiled
- 6 passed and were eligible

Baseline failures are dataset/environment exclusions, not DeepSeek repair
failures. They were never sent to the model.

## Threats to Validity

- The evaluation is a controlled DataTD sample, not the entire 30 GB dataset.
- The held-out cohort has 17 candidates and only four original smell categories.
- Projects and smell categories are not statistically independent.
- Test-suite pass status does not guarantee full semantic equivalence.
- DeepSeek service behavior can vary despite a frozen prompt.
- Cost is estimated from reported token classes and published rates.
- One candidate required an infrastructure-only rerun.

## Recommended Improvements

- Add Java parser validation before Maven.
- Add assertion-preservation checks to reject obvious semantic weakening.
- Add JaCoCo and PIT on representative accepted repairs.
- Increase the held-out cohort and diversify rare smell categories.
- Run from a single uninterrupted worker or external job runner instead of an
  interactive tool timeout window.
