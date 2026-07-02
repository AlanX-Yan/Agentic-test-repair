# AromaDr Java Test Repair MVP

This MVP implements the architecture from the revised proposal:

1. A coding agent generates Java tests.
2. A Java execution harness compiles and runs them.
3. A detector layer runs AromaDr when configured, with a lightweight fallback for this local demo.
4. A master evaluator checks build status, test status, and smell findings.
5. A feedback generator turns findings into repair instructions.
6. The coding agent repairs the tests and the loop repeats.

The local demo supports both zero-dependency `javac-demo` tasks and a real Maven/JUnit 5 task. Maven is available in `../tools/apache-maven-3.9.16`, and the harness automatically uses it when a task sets `"build_tool": "maven"`. The `javac-demo` tasks still use JUnit-style tests with a tiny local `org.junit.jupiter.api` stub and reflection launcher so they remain runnable without downloading dependencies.

## Quick Start

Run from this directory:

```bash
python3 -m test_repair_mvp
```

Expected result:

```text
Goal-driven Java test repair MVP complete
Task: calculator-java-demo
Iterations: 2
Initial smells: 4
Final smells: 0
Final accepted: True
Artifacts: .../.mvp_runs/latest/artifacts
```

Open the generated report:

```bash
cat .mvp_runs/latest/artifacts/report.md
```

Run the proposal-style benchmark evaluation:

```bash
python3 -m test_repair_mvp --benchmark demo/config/benchmark.json --run-dir .mvp_runs/benchmark
```

Current benchmark demo result:

```text
Tasks: 3
Accepted: 3
Initial smells: 12
Final smells: 0
```

With AromaDr running and `AROMADR_API_URL=http://localhost:3000`, the benchmark currently reports:

```text
Tasks: 3
Accepted: 3
Initial smells: 15
Final smells: 0
Smell delta: 15
```

Open aggregate outputs:

```bash
cat .mvp_runs/benchmark/benchmark_report.md
cat .mvp_runs/benchmark/benchmark_results.csv
```

## AromaDr Integration

The preferred integration is AromaDr's HTTP API. Start AromaDr separately, then set `AROMADR_API_URL`:

```bash
AROMADR_API_URL="http://localhost:3000" python3 -m test_repair_mvp --benchmark demo/config/benchmark.json --run-dir .mvp_runs/benchmark-aromadr
```

The detector posts each generated JUnit test file to:

```text
POST /file-test-smells/detect
{
  "language": "java",
  "framework": "junit",
  "testFileContent": "..."
}
```

It parses AromaDr's real response shape: `testSuites[].tests[].testSmells[]`, where each smell has `name`, `startLine`, `startColumn`, `endLine`, and `endColumn`.

`AROMADR_CMD` is still supported for command-line experiments. The command can use `{project_root}` and `{test_file}` placeholders:

```bash
AROMADR_CMD="java -jar /path/to/aromadr.jar --project {project_root} --test {test_file}" python3 -m test_repair_mvp
```

The adapter accepts a normalized CSV-like output:

```text
file,line,smell,message
src/test/java/com/example/CalculatorBehaviorTest.java,8,MissingAssertion,No meaningful assertion
```

The command adapter accepts JSON list/object outputs with fields such as `file`, `path`, `line`, `startLine`, `smell_type`, `type`, `smell`, `message`, or `description`.

If AromaDr is not running, the detector records `aroma_dr_available=false` and falls back to the local lightweight JUnit checks so the repair loop remains demoable.

## Project Layout

```text
test_repair_mvp/
  agents.py          coding-agent interface and deterministic demo agent
  harness.py         Java execution harness for javac-demo, Maven, and Gradle
  detectors.py       AromaDr adapter plus lightweight local detector
  feedback.py        master evaluator and feedback generator
  orchestrator.py    goal-driven repair loop
  reporting.py       iteration snapshots and final reports
  benchmark.py       multi-task paired before-after evaluation
demo/
  java_project/      calculator Java target used by the demo
  string_project/    string sanitizer Java target used by the benchmark
  maven_calculator_project/ real Maven/JUnit 5 benchmark target
  config/            task and benchmark configuration
docs/
  ARCHITECTURE.md    full architecture and extension plan
  AROMADR_INTEGRATION.md exact AromaDr API wiring notes
```

## MVP Boundaries

- The demo agent is deterministic so the pipeline is reproducible.
- The generated tests are JUnit-style, but the local demo uses a tiny JUnit API stub so it can run without downloading dependencies.
- The local detector is not a replacement for AromaDr; it exists so the demo runs when the AromaDr service is not currently available.
- The current deterministic repair templates address the AromaDr smells observed so far: `UnknownTest`, `MagicNumberTest`, `AssertionRoulette`, and `ExceptionHandling`.
- Gradle, JaCoCo, PIT, and real LLM-based coding agents are explicit next integration points.
