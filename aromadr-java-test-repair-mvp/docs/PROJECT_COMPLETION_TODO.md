# Project Completion TODO

Last updated: 2026-07-30

Status: `[x]` complete, `[-]` in progress, `[ ]` pending, `[~]` optional.

## DeepSeek V2 Extension

- [x] Expand baseline-only discovery across the extracted DataTD corpus.
- [x] Freeze 26 additional strict-eligible candidates from 10 projects.
- [x] Verify zero overlap with the v1 held-out cohort and zero v2 duplicates.
- [x] Split the frozen cohort into 24 JDK 21 and 2 JDK 11 candidates.
- [x] Freeze `deepseek-v2` semantics and the CNY 30 / USD 4.00 conservative
  execution boundary in `docs/EVALUATION_PROTOCOL_V2.md`.
- [x] Inject the DeepSeek credentials into the execution environment without
  storing them in repository artifacts.
- [x] Run all 26 v2 candidates to terminal outcomes.
- [x] Combine v1 and v2 formal metrics using the achieved denominator of 43.
- [x] Semantically review representative accepted v2 diffs.
- [x] Update reports, archive secret-free summaries, run all tests, and
  publish the extension to the existing GitHub pull request.

The requested formal total was 50. Strict screening produced only 26 new
eligible candidates, so the evidence-supported total is 43. The remaining
seven must not be filled with baseline-failing candidates.

## Current Verified Baseline

- [x] Maven/DataTD scanner and AromaDr integration
- [x] Fixed 40-file subset selected from 83 AromaDr candidates
- [x] Isolated candidate-to-repair adapter
- [x] DeepSeek V4 Pro backend with structured output validation
- [x] Maven/AromaDr feedback loop, failure isolation, and rollback
- [x] Ten-candidate development cohort
- [x] Four of four eligible development repairs accepted
- [x] Development AromaDr findings reduced from 136 to 0
- [x] Original DataTD source hash protection
- [x] Core documentation updated for the real backend

The development cohort used 6 model calls, 93,651 recorded tokens, and an
estimated USD 0.0606. It was used to tune the runner and is not held-out data.

## P0 — Reliable Experiment Runner

Complete all P0 items before the first held-out model call.

- [x] Add candidate-level failure isolation.
  - Complete when one API/candidate failure does not stop the batch and the
    isolated test is restored.
- [x] Add empty/invalid JSON format recovery.
  - Complete when one sanitized non-thinking recovery is attempted and recorded.
- [x] Add `--repair-offset` for non-overlapping batches.
- [x] Add `--repair-budget-usd`.
  - Stop before a request that would exceed the configured maximum.
  - Report configured, consumed, and remaining estimated budget.
- [x] Calculate cache-hit, cache-miss, and output cost separately.
- [x] Record every logical API attempt, including failed and format-recovery requests.
- [x] Add bounded retry for HTTP 429/500/502/503 and network timeouts.
- [x] Add resumable output and completed-candidate skipping.
- [x] Preserve successful baseline metrics if a later API step fails.
- [x] Add aggregate/CSV fields:
  - baseline/final AromaDr counts
  - diff path and error
  - elapsed seconds
  - provider/model
  - attempts/tokens/cost
  - accepted/rollback status
- [x] Record prompt hash, input-source hash, and response hash.
- [x] Write `environment.json` with Python, Java, Maven, OS, model, AromaDr,
  timeouts, attempt limit, candidate subset identity, and command options.
- [-] Add tests for format recovery, transient retry, budget stop, resume,
  candidate isolation, rollback, offset, and API-key non-disclosure.
- [ ] Run and archive the complete automated test result.

## P1 — Freeze the Evaluation Configuration

- [x] Assign protocol version `deepseek-v1`.
- [x] Freeze the system prompt and feedback templates.
- [x] Freeze model, thinking mode, output limit, and two repair attempts.
- [x] Freeze AromaDr-authoritative acceptance rules.
- [x] Freeze Maven repository and timeout strategy.
- [x] Record configuration and prompt hashes.
- [x] Mark candidates 1–10 as development data.
- [x] Prohibit prompt tuning after held-out evaluation begins.
- [x] Document the rule for unavoidable post-freeze infrastructure changes.

Complete when a checked-in manifest identifies every immutable evaluation
setting.

## P2 — Held-Out Cohort

- [x] Baseline-screen fixed-subset candidates 11–40 without API calls.
- [x] Record compile failure, test failure, timeout, AromaDr availability, and
  eligibility for each row.
- [x] Select 17 eligible held-out candidates.
- [x] Candidates 11–40 were insufficient; draw deterministic replacements
  from the remaining 83-candidate pool.
- [x] Preserve project diversity and limit replacement files per project.
- [x] Record pre-run smell-type coverage.
- [x] Create a path-neutral cohort manifest containing project IDs, relative
  test paths, hashes, and smell types.

Complete when the cohort is frozen before its first DeepSeek call.

## P3 — Formal Held-Out Evaluation

- [x] Run the frozen configuration on every held-out eligible candidate.
- [x] Do not tune prompts against held-out results.
- [x] Verify Maven compile and tests after each proposal.
- [x] Verify AromaDr before/after findings.
- [x] Verify only the authorized isolated test file changes.
- [x] Verify every original DataTD hash remains unchanged.
- [x] Record accepted, rejected, rolled-back, skipped, timed-out, API-error,
  and infrastructure-error outcomes.
- [x] Preserve representative successful and failed diffs.
- [x] Investigate infrastructure failures without relabeling model failures.

Complete when each held-out candidate has one terminal auditable outcome.

## P4 — Analysis

- [x] Screening, build, test, and eligibility table.
- [x] Repair success rate with an explicit denominator.
- [x] First-attempt versus feedback-retry success.
- [x] AromaDr before/after counts and reduction percentage.
- [x] Per-smell-type success table.
- [x] Per-project success table.
- [x] Build/test regression counts.
- [x] Skip and non-candidate reason breakdown.
- [x] API/infrastructure failure breakdown.
- [x] Token, cache, cost, call-count, and runtime distributions.
- [x] Keep development and held-out results separate.
- [x] Manually review at least 10 accepted diffs for:
  - deleted or weakened assertions
  - meaningless assertions
  - changed test intent
  - new timing/flakiness
  - unauthorized dependency or production changes
- [~] Add JaCoCo on a representative subset.
- [~] Add PIT mutation testing on a smaller subset.

Complete when every final claim is regenerable from experiment artifacts.

## P5 — Final Reports

- [x] Create `docs/DATATD_RESULTS.md`.
- [x] Create `docs/REPAIR_EVALUATION.md`.
- [x] Create `docs/FAILURE_ANALYSIS.md`.
- [x] Create an advisor-facing executive summary.
- [x] State whether DataTD coverage is full-dataset or sampled-batch.
- [x] Explain why smelly files become ineligible.
- [x] Explain AromaDr-authoritative versus lightweight diagnostic findings.
- [x] Document what code/context is sent to DeepSeek.
- [x] Document limitations and threats to validity.
- [x] Include representative before/after examples and semantic-review findings.
- [x] Add the exact frozen reproduction command to the protocol and link it from README.
- [x] Label every reported figure as development or held-out.

## P6 — Reproducible Public Artifacts

- [x] Produce path-neutral, secret-free result CSV/JSON.
- [x] Keep request IDs only in ignored raw artifacts; omit them from publishable results.
- [x] Search publishable artifacts for API keys and authorization headers.
- [x] Confirm DataTD, `.m2`, `.mvp_runs`, and raw logs remain ignored.
- [x] Publish the environment and command manifest.
- [x] Provide mock HTTP fixtures so tests never incur API cost.
- [x] Run tests from a clean checkout/worktree after the publication commit.
- [x] Declare the supported Python version and dependency metadata.
- [x] Update stale top-level handoff/completion documents.

## P7 — Repository and Advisor Delivery

- [x] Review the worktree scope; listed changes belong to the DataTD/DeepSeek project.
- [x] Run the full test suite and `git diff --check`.
- [x] Inspect `git status` for secrets, datasets, caches, and generated logs.
- [x] Commit source, tests, docs, and small summaries intentionally.
- [x] Push the selected branch to GitHub.
- [x] Verify GitHub Markdown links and rendering.
- [x] Prepare advisor-facing results and limitation talking points.
- [x] Record publication baseline commit `f7b63a1` for the evaluated artifacts.

## Definition of Done

The project is complete when:

1. The runner is budgeted, resumable, failure-isolated, and tested.
2. A frozen held-out cohort has terminal results under immutable settings.
3. Build, test, AromaDr, semantic-review, failure, runtime, token, and cost
   metrics are reported.
4. Results are reproducible from path-neutral, secret-free artifacts.
5. Public documentation distinguishes development from held-out evaluation.
6. The repository is clean, tested, committed, pushed, and advisor-ready.
