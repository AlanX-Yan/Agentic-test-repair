# Manual Semantic Review

Ten automatically accepted held-out repairs were manually reviewed. The review
checked assertion preservation, meaningless assertions, changed intent,
flakiness, and unauthorized production/dependency changes.

## Summary

| Outcome | Count |
| --- | ---: |
| Clean pass | 7 |
| Pass with minor caution | 1 |
| Manual quality failure | 2 |
| Reviewed | 10 |

All ten diffs changed only the authorized test file. SHA-256 comparison of each
copied project's `src/main` files and `pom.xml` against DataTD found no
production or dependency changes.

## Passed Reviews

- `RetryServiceUnitTest`: behavior checks preserved after test splitting.
  Caution: a new non-null exception-message assertion slightly strengthens and
  may overconstrain the contract.
- `JsonErrorTest`: Hamcrest equality converted to equivalent JUnit equality.
- `CfEnvS3ProcessorUnitTest`: existing assertions preserved with messages.
- `CityControllerTest`: exact assertions and Mockito verifications preserved.
- `WelcomeControllerAcceptanceTest`: status/body equality preserved.
- `RoleTest`: 69 assertions preserved; constants/messages only.
- `ArtigoTest`: seven oracles preserved one-for-one.
- `ApplicationIntegrationTest`: stream `anyMatch` remains an equivalent
  existence check.

## Manual Quality Failures

### AsFilterServletContainerProviderTest

The proposal added four assertions equivalent to:

```java
assertTrue("...", true);
```

These assertions are permanently true and cannot detect a defect. Existing
Mockito verifications already exercised the behavior. This is smell gaming:
the automated AromaDr/Maven gate accepted the file, but the new oracle is
meaningless.

### RotinaDiurnaIntegrationTest

The proposal duplicated one slow integration flow into two tests to separate
assertions. Production behavior sleeps about 40 ms for each of 500 invoices.
The repaired tests took approximately 23.4 seconds each under a 25-second
timeout, doubling the expensive flow and leaving little CI margin. Assertions
were meaningful, but the repair introduced a material flakiness/runtime risk.

## Interpretation

The primary reported success remains the prespecified automated result:
15 of 17 repairs passed Maven and AromaDr. Manual review shows that automated
acceptance is not sufficient for semantic quality. Of ten reviewed accepted
repairs, eight were acceptable (one with caution) and two should be rejected
under a stricter human quality gate.

Future automation should reject constant-true assertions, compare assertion
strength, and flag large runtime/test-count increases.
