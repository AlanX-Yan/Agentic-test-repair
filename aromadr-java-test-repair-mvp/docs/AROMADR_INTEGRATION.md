# AromaDr Integration

## Current Status

AromaDr has been cloned into:

```text
../external/aromadr
```

This repository is a TypeScript/Docker service, not a Maven library. The relevant API endpoint is:

```text
POST http://localhost:3000/file-test-smells/detect
```

The detector in `test_repair_mvp/detectors.py` now supports this endpoint through the `AROMADR_API_URL` environment variable.

## Running With AromaDr

Start AromaDr first. The upstream README recommends Docker:

```bash
docker run --rm -it -p 3000:3000 -p 8000:8000 publioblenilio/aromadr
```

Then run this project with:

```powershell
cd path\to\Agentic-Test-Repair\aromadr-java-test-repair-mvp
$env:AROMADR_API_URL = "http://localhost:3000"
python -m test_repair_mvp --benchmark demo/config/benchmark.json --run-dir .mvp_runs/benchmark-aromadr
```

If Docker is not installed, the project still runs with the lightweight fallback detector. Reports will mark AromaDr as unavailable.

## Request Payload

For each generated or repaired test file, the MVP sends:

```json
{
  "language": "java",
  "framework": "junit",
  "testFileContent": "..."
}
```

This matches AromaDr's documented file-level API.

## Response Parsing

AromaDr's controller returns:

```json
{
  "testFileAST": {},
  "testSuites": [
    {
      "testSuite": {},
      "tests": [
        {
          "test": { "name": "testName" },
          "testSmells": [
            {
              "name": "AssertionRoulette",
              "startLine": 10,
              "startColumn": 5,
              "endLine": 10,
              "endColumn": 20
            }
          ]
        }
      ]
    }
  ]
}
```

The MVP normalizes each smell into `SmellFinding`:

- `smell_type`: AromaDr smell `name`
- `file`: generated test file path
- `line`: `startLine`
- `message`: concise repair context
- `source`: `AromaDr`

The evaluator and feedback generator consume the normalized `SmellReport`.
When AromaDr is available, only its findings are authoritative for acceptance
and feedback; lightweight findings remain diagnostic.

## Fallback Behavior

When `AROMADR_API_URL` is not set, or when the API cannot be reached:

1. The report records `aroma_dr_available=false`.
2. The local lightweight JUnit detector runs.
3. The goal-driven loop remains executable for demos and plumbing development.

DeepSeek repair eligibility for DataTD still requires AromaDr to be available.

## Deterministic Template Strategies

The repair loop now handles the AromaDr smells observed in the benchmark:

| AromaDr smell | Repair strategy |
| --- | --- |
| `UnknownTest` | Ensure each test contains an AromaDr-recognized assertion such as `Assert.assertEquals`, `Assert.assertTrue`, or `Assert.fail`. Avoid relying only on `assertThrows`, which AromaDr does not currently treat as an assertion. |
| `MagicNumberTest` | Move numeric literals out of assertion arguments and into named constants such as `EXPECTED_SUM`, `DIVIDEND`, or `MAX_BOUND`. |
| `AssertionRoulette` | Split multi-assertion tests into focused one-assertion tests, and use message-first `Assert` assertions so AromaDr can read the assertion message. |
| `ExceptionHandling` | Move `try/catch` exception verification into a non-test helper method, then assert the helper result from the test method. This preserves behavior checking while keeping the test body free of exception-handling statements. |

The DeepSeek backend is not limited to these templates. It receives the real
candidate findings and is accepted only after Maven and AromaDr validation.

Current AromaDr-backed benchmark result:

```text
Tasks: 3
Accepted: 3
Initial smells: 15
Final smells: 0
Smell delta: 15
```

The DataTD development cohort separately screened 10 candidates and accepted
all 4 strictly eligible DeepSeek repairs, reducing authoritative AromaDr
findings from 136 to 0. It is development data, not held-out evaluation.
