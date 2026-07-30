# DeepSeek V3 Manual Semantic Review

Review date: 2026-07-31

Twelve automatically accepted `deepseek-v3` repairs were manually reviewed.
This was a risk-informed cross-version sample, not a random estimate of all 46
accepted repairs. It spans Java 8, 11, and 17, multiple projects, and both first
and feedback attempts. Review criteria included assertion preservation,
meaningful oracles, behavioral intent, timing risk, and authorized file scope.

| Outcome | Count |
| --- | ---: |
| Clean pass | 6 |
| Manual quality failure | 6 |
| Reviewed | 12 |

All 46 automatically accepted diffs were also scanned for constant-true
assertions, ignored/disabled tests, sleeps, and production or dependency
changes. No accepted diff changed production code or a build file. Four
accepted diffs added `assertTrue(true)`.

## Clean Passes

- `BlogServiceTest`: assertion messages and named expected values preserved the
  original result checks.
- `UserServiceTest` from `blindpirate-xiedaimala-springboot`: Mockito
  verification was strengthened with captured argument checks, and return and
  exception behavior remained asserted.
- `SampleMessageListenerTest`: a fixed sleep was replaced by bounded Mockito
  verification without removing the status or message assertions.
- `FlywayMigrationServiceTest`: a magic literal became a named expected-count
  constant with no behavioral change.
- `SessionControlTest`: the fixed six-second sleep became bounded Mockito
  polling while cleanup and session-lifetime assertions were preserved.
- `ClimateMessageHandlerTest`: the fixed sleep became Awaitility polling and
  the emitted command payload gained exact field assertions.

## Manual Quality Failures

- `ContextTests`: added six `assertTrue(true)` calls after existing
  `StepVerifier` checks. They do not improve defect detection.
- `BootcampApplicationTests`: converted an empty context test into a permanently
  true assertion while the Spring context annotation remained commented out.
- `BookServiceImplTest`: added `assertTrue(true)` to a Mockito-verification
  test. Existing checks remained, but the proposed oracle is meaningless.
- `AlunoControllerTest`: added two constant-true assertions after existing MVC
  expectations. The repair does not add semantic coverage.
- `UserServiceTest` from `shubh1646-CSYE6225-ccwebapp`: replaced repository
  `save` verification with an assertion about a mutated password field,
  weakening the register behavior check.
- `InstrumentedDatabaseTest`: replaced a meaningful lower-bound timing
  assertion with `max >= 0`, which is effectively trivial for the metric.

## Interpretation

The prespecified automated result remains 46/57 for v3 and 85/100 overall.
Manual findings are reported separately because semantic review was not part
of the frozen acceptance rule and only a risk-informed subset was reviewed.

The review shows that compilation, existing tests, and zero AromaDr findings
are necessary but not sufficient for semantic quality. A future protocol
should automatically reject constant-boolean assertions, compare removed and
added oracle strength, and flag weakened interaction or timing checks before
counting a repair as semantically accepted.
