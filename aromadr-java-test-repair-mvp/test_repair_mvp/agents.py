from __future__ import annotations

import json
import hashlib
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .models import ProjectTask
from .utils import write_json


class CodingAgent(Protocol):
    def generate_initial_tests(self, task: ProjectTask) -> None: ...

    def repair_tests(self, task: ProjectTask, feedback: str, iteration: int) -> None: ...


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-pro"
    timeout_seconds: int = 300
    max_tokens: int = 16_384
    thinking: str = "enabled"

    @classmethod
    def from_env(cls) -> "DeepSeekConfig":
        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured.")
        return cls(
            api_key=api_key,
            base_url=os.environ.get(
                "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
            ).rstrip("/"),
            model=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro"),
            timeout_seconds=int(os.environ.get("DEEPSEEK_TIMEOUT_SECONDS", "300")),
            max_tokens=int(os.environ.get("DEEPSEEK_MAX_TOKENS", "16384")),
            thinking=os.environ.get("DEEPSEEK_THINKING", "enabled"),
        )


class BudgetExceededError(RuntimeError):
    pass


@dataclass
class ApiBudget:
    limit_usd: float | None = None
    consumed_usd: float = 0.0

    def authorize(self, reserved_usd: float) -> None:
        if (
            self.limit_usd is not None
            and self.consumed_usd + reserved_usd > self.limit_usd
        ):
            raise BudgetExceededError(
                f"API budget would be exceeded: consumed=${self.consumed_usd:.6f}, "
                f"reserved=${reserved_usd:.6f}, limit=${self.limit_usd:.6f}"
            )

    def consume(self, actual_usd: float) -> None:
        self.consumed_usd += actual_usd


class DeepSeekCodingAgent:
    """Repair one authorized Java test file through DeepSeek Chat Completions."""

    def __init__(
        self,
        config: DeepSeekConfig,
        artifacts_dir: Path,
        *,
        budget: ApiBudget | None = None,
    ) -> None:
        self.config = config
        self.budget = budget or ApiBudget()
        self.artifacts_dir = artifacts_dir
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.call_records: list[dict] = []

    def generate_initial_tests(self, task: ProjectTask) -> None:
        existing = task.test_file.read_text(encoding="utf-8") if task.test_file.exists() else ""
        self._generate_and_write(
            task,
            "Create the requested Java test file.",
            existing,
            iteration=0,
        )

    def repair_tests(self, task: ProjectTask, feedback: str, iteration: int) -> None:
        existing = task.test_file.read_text(encoding="utf-8")
        self._generate_and_write(task, feedback, existing, iteration=iteration)

    def _generate_and_write(
        self,
        task: ProjectTask,
        feedback: str,
        original_source: str,
        *,
        iteration: int,
    ) -> None:
        self._validate_target_path(task)
        request_body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {
                    "role": "user",
                    "content": self._user_prompt(task, feedback, original_source),
                },
            ],
            "response_format": {"type": "json_object"},
            "thinking": {"type": self.config.thinking},
            "max_tokens": self.config.max_tokens,
            "stream": False,
        }
        response = self._request_with_budget(request_body, iteration, "repair")
        try:
            message = response["choices"][0]["message"]["content"]
            proposal = self._parse_proposal(message)
        except (KeyError, IndexError, TypeError, ValueError) as first_error:
            self._record_format_error(iteration, response, first_error)
            recovery_body = dict(request_body)
            recovery_body["thinking"] = {"type": "disabled"}
            recovery_body["messages"] = request_body["messages"] + [
                {
                    "role": "user",
                    "content": (
                        "Your previous response was empty or invalid. Return the "
                        "required JSON object only, with a complete replacement_source."
                    ),
                }
            ]
            response = self._request_with_budget(
                recovery_body, iteration, "format-recovery"
            )
            message = response["choices"][0]["message"]["content"]
            proposal = self._parse_proposal(message)
        replacement = proposal["replacement_source"]
        self._validate_replacement(task, original_source, replacement)
        temporary = task.test_file.with_suffix(task.test_file.suffix + ".deepseek.tmp")
        temporary.write_text(replacement, encoding="utf-8")
        temporary.replace(task.test_file)
        self._record_call(iteration, response, proposal)

    def _post_json(self, body: dict) -> dict:
        request = urllib.request.Request(
            f"{self.config.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(
                    request, timeout=self.config.timeout_seconds
                ) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                detail = error.read().decode("utf-8", errors="replace")[:2000]
                last_error = RuntimeError(
                    f"DeepSeek API returned HTTP {error.code}: {detail}"
                )
                if error.code not in {429, 500, 502, 503} or attempt >= 2:
                    raise last_error from error
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                last_error = RuntimeError(f"DeepSeek API request failed: {error}")
                if attempt >= 2:
                    raise last_error from error
            time.sleep(2**attempt)
        raise RuntimeError(f"DeepSeek API request failed: {last_error}")

    def _request_with_budget(
        self,
        body: dict,
        iteration: int,
        request_kind: str,
    ) -> dict:
        reserved = self._reserved_request_cost(body)
        self.budget.authorize(reserved)
        prompt_sha256 = hashlib.sha256(
            json.dumps(
                body.get("messages") or [],
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        started = time.monotonic()
        try:
            response = self._post_json(body)
        except Exception as error:
            self._record_api_attempt(
                iteration,
                request_kind,
                status="error",
                elapsed_seconds=time.monotonic() - started,
                error=type(error).__name__,
                prompt_sha256=prompt_sha256,
            )
            raise
        actual = self._usage_cost(response.get("usage") or {})
        self.budget.consume(actual)
        self._record_api_attempt(
            iteration,
            request_kind,
            status="completed",
            elapsed_seconds=time.monotonic() - started,
            response=response,
            estimated_cost_usd=actual,
            prompt_sha256=prompt_sha256,
        )
        return response

    def _reserved_request_cost(self, body: dict) -> float:
        serialized = json.dumps(body.get("messages") or [], ensure_ascii=False)
        estimated_input_tokens = max(1, len(serialized) // 4)
        estimated_output_tokens = int(body.get("max_tokens") or 0)
        return (
            estimated_input_tokens / 1_000_000 * 0.435
            + estimated_output_tokens / 1_000_000 * 0.87
        )

    def _usage_cost(self, usage: dict) -> float:
        details = usage.get("prompt_tokens_details") or {}
        cache_hit = int(
            usage.get("prompt_cache_hit_tokens")
            or details.get("cached_tokens")
            or 0
        )
        prompt_total = int(usage.get("prompt_tokens") or 0)
        cache_miss = int(
            usage.get("prompt_cache_miss_tokens")
            or max(0, prompt_total - cache_hit)
        )
        completion = int(usage.get("completion_tokens") or 0)
        return (
            cache_hit / 1_000_000 * 0.003625
            + cache_miss / 1_000_000 * 0.435
            + completion / 1_000_000 * 0.87
        )

    def _record_api_attempt(
        self,
        iteration: int,
        request_kind: str,
        *,
        status: str,
        elapsed_seconds: float,
        response: dict | None = None,
        estimated_cost_usd: float = 0.0,
        error: str = "",
        prompt_sha256: str = "",
    ) -> None:
        path = self.artifacts_dir / "api_attempts.json"
        attempts: list[dict] = []
        if path.exists():
            attempts = json.loads(path.read_text(encoding="utf-8"))
        response = response or {}
        choice = (response.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content") or ""
        attempts.append(
            {
                "iteration": iteration,
                "request_kind": request_kind,
                "status": status,
                "model": response.get("model", self.config.model),
                "request_id": response.get("id"),
                "finish_reason": choice.get("finish_reason"),
                "usage": response.get("usage") or {},
                "prompt_sha256": prompt_sha256,
                "response_sha256": (
                    hashlib.sha256(content.encode("utf-8")).hexdigest()
                    if content
                    else ""
                ),
                "estimated_cost_usd": round(estimated_cost_usd, 8),
                "elapsed_seconds": round(elapsed_seconds, 3),
                "error": error,
            }
        )
        write_json(path, attempts)

    def _system_prompt(self) -> str:
        return (
            "You are a Java test-repair agent. Return one JSON object with keys "
            '"replacement_source", "rationale", "addressed_smells", and '
            '"assumptions". replacement_source must contain the complete Java test '
            "file with no Markdown fences. Preserve intended behavior; do not delete "
            "tests or assertions to hide failures; do not modify production code, "
            "dependencies, package name, or public top-level class name. Make the "
            "smallest focused repair."
        )

    def _user_prompt(
        self,
        task: ProjectTask,
        feedback: str,
        original_source: str,
    ) -> str:
        sections = [
            f"Task: {task.target_description}",
            f"Authorized test file: {task.test_file.relative_to(task.project_root)}",
            "Repair feedback:\n" + feedback,
            "Current test file:\n" + original_source,
        ]
        pom = task.project_root / "pom.xml"
        if pom.exists():
            sections.append("pom.xml:\n" + self._read_limited(pom, 40_000))
        production_context = self._production_context(task, max_chars=100_000)
        if production_context:
            sections.append("Production context (read-only):\n" + production_context)
        sections.append(
            "Return valid JSON only. replacement_source must be a JSON string "
            "containing the complete compilable Java file."
        )
        return "\n\n".join(sections)

    def _production_context(self, task: ProjectTask, *, max_chars: int) -> str:
        root = task.project_root / "src" / "main" / "java"
        if not root.exists():
            return ""
        chunks: list[str] = []
        used = 0
        for path in sorted(root.rglob("*.java")):
            source = self._read_limited(path, max_chars - used)
            chunk = f"// {path.relative_to(task.project_root)}\n{source}"
            if used + len(chunk) > max_chars:
                break
            chunks.append(chunk)
            used += len(chunk)
        return "\n\n".join(chunks)

    def _read_limited(self, path: Path, limit: int) -> str:
        if limit <= 0:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")[:limit]

    def _parse_proposal(self, content: str) -> dict:
        if "```" in content:
            raise ValueError("DeepSeek response contains a Markdown code fence.")
        try:
            proposal = json.loads(content)
        except json.JSONDecodeError as error:
            raise ValueError("DeepSeek response is not valid JSON.") from error
        if not isinstance(proposal, dict):
            raise ValueError("DeepSeek response must be a JSON object.")
        replacement = proposal.get("replacement_source")
        if not isinstance(replacement, str) or not replacement.strip():
            raise ValueError("DeepSeek response has no replacement_source.")
        return proposal

    def _validate_target_path(self, task: ProjectTask) -> None:
        project = task.project_root.resolve()
        target = task.test_file.resolve()
        if target != project and project not in target.parents:
            raise ValueError(f"Test file escapes project root: {target}")
        if target.suffix.lower() != ".java":
            raise ValueError(f"Authorized target is not a Java file: {target}")

    def _validate_replacement(
        self,
        task: ProjectTask,
        original: str,
        replacement: str,
    ) -> None:
        if "\x00" in replacement or "```" in replacement:
            raise ValueError("Replacement contains invalid wrapper content.")
        original_package = self._package_name(original)
        replacement_package = self._package_name(replacement)
        if original and original_package != replacement_package:
            raise ValueError("Replacement changed the Java package.")
        public_classes = re.findall(
            r"\bpublic\s+(?:final\s+|abstract\s+)?class\s+([A-Za-z_$][\w$]*)",
            replacement,
        )
        if public_classes and task.test_file.stem not in public_classes:
            raise ValueError("Replacement public class does not match the file name.")

    def _package_name(self, source: str) -> str:
        match = re.search(r"(?m)^\s*package\s+([\w.]+)\s*;", source)
        return match.group(1) if match else ""

    def _record_call(self, iteration: int, response: dict, proposal: dict) -> None:
        usage = response.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        estimated_cost = self._usage_cost(usage)
        record = {
            "iteration": iteration,
            "provider": "deepseek",
            "model": response.get("model", self.config.model),
            "request_id": response.get("id"),
            "finish_reason": (response.get("choices") or [{}])[0].get("finish_reason"),
            "usage": usage,
            "estimated_cost_usd": round(estimated_cost, 8),
            "rationale": proposal.get("rationale", ""),
            "addressed_smells": proposal.get("addressed_smells", []),
            "assumptions": proposal.get("assumptions", []),
        }
        self.call_records.append(record)
        write_json(self.artifacts_dir / "model_calls.json", self.call_records)

    def _record_format_error(
        self,
        iteration: int,
        response: dict,
        error: Exception,
    ) -> None:
        errors_path = self.artifacts_dir / "model_format_errors.json"
        errors: list[dict] = []
        if errors_path.exists():
            errors = json.loads(errors_path.read_text(encoding="utf-8"))
        choice = (response.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        errors.append(
            {
                "iteration": iteration,
                "model": response.get("model", self.config.model),
                "request_id": response.get("id"),
                "finish_reason": choice.get("finish_reason"),
                "content_length": len(message.get("content") or ""),
                "usage": response.get("usage") or {},
                "error": type(error).__name__,
            }
        )
        write_json(errors_path, errors)


def create_coding_agent(
    backend: str,
    artifacts_dir: Path,
    *,
    budget: ApiBudget | None = None,
) -> CodingAgent:
    if backend == "template":
        return TemplateCodingAgent()
    if backend == "deepseek":
        return DeepSeekCodingAgent(
            DeepSeekConfig.from_env(), artifacts_dir, budget=budget
        )
    raise ValueError(f"Unsupported coding backend: {backend}")


class TemplateCodingAgent:
    """Deterministic stand-in for a coding agent.

    The interface is intentionally small so this MVP can later swap in Codex,
    Claude Code, Copilot, or another agent without changing the orchestrator.
    """

    def generate_initial_tests(self, task: ProjectTask) -> None:
        task.test_file.parent.mkdir(parents=True, exist_ok=True)
        if "string" in task.task_id:
            task.test_file.write_text(self._initial_string_test_source(), encoding="utf-8")
        else:
            task.test_file.write_text(self._initial_calculator_test_source(), encoding="utf-8")

    def repair_tests(self, task: ProjectTask, feedback: str, iteration: int) -> None:
        if "string" in task.task_id:
            task.test_file.write_text(self._repaired_string_test_source(), encoding="utf-8")
        else:
            task.test_file.write_text(self._repaired_calculator_test_source(), encoding="utf-8")

    def _initial_calculator_test_source(self) -> str:
        return """package com.example;

import org.junit.jupiter.api.Test;

public class CalculatorBehaviorTest {
    @Test
    void testBasic() {
        Calculator calc = new Calculator();
        calc.add(1, 2);
        calc.divide(4, 2);
        calc.clamp(15, 0, 10);
    }
}
"""

    def _repaired_calculator_test_source(self) -> str:
        return """package com.example;

import org.junit.jupiter.api.Test;

import org.junit.Assert;

public class CalculatorBehaviorTest {
    private static final int LEFT_ADDEND = 1;
    private static final int RIGHT_ADDEND = 2;
    private static final int EXPECTED_SUM = 3;
    private static final int DIVIDEND = 4;
    private static final int DIVISOR = 2;
    private static final int EXPECTED_QUOTIENT = 2;
    private static final int VALUE_ABOVE_MAX = 15;
    private static final int VALUE_BELOW_MIN = -5;
    private static final int MIN_BOUND = 0;
    private static final int MAX_BOUND = 10;
    private static final int ZERO_DIVISOR = 0;

    @Test
    void testAddReturnsSumForPositiveIntegers() {
        Calculator calc = new Calculator();
        Assert.assertEquals("add should return the arithmetic sum",
                EXPECTED_SUM, calc.add(LEFT_ADDEND, RIGHT_ADDEND));
    }

    @Test
    void testDivideReturnsIntegerQuotient() {
        Calculator calc = new Calculator();
        Assert.assertEquals("divide should return integer quotient",
                EXPECTED_QUOTIENT, calc.divide(DIVIDEND, DIVISOR));
    }

    @Test
    void testClampCapsValueAboveMaximum() {
        Calculator calc = new Calculator();
        Assert.assertEquals("clamp should cap values above max",
                MAX_BOUND, calc.clamp(VALUE_ABOVE_MAX, MIN_BOUND, MAX_BOUND));
    }

    @Test
    void testClampLiftsValueBelowMinimum() {
        Calculator calc = new Calculator();
        Assert.assertEquals("clamp should lift values below min",
                MIN_BOUND, calc.clamp(VALUE_BELOW_MIN, MIN_BOUND, MAX_BOUND));
    }

    @Test
    void testDivideByZeroThrowsArithmeticException() {
        Calculator calc = new Calculator();
        Assert.assertTrue("divide by zero should throw ArithmeticException",
                divideByZeroThrowsArithmeticException(calc));
    }

    private boolean divideByZeroThrowsArithmeticException(Calculator calc) {
        try {
            calc.divide(DIVIDEND, ZERO_DIVISOR);
            return false;
        } catch (ArithmeticException expected) {
            return true;
        }
    }
}
"""

    def _initial_string_test_source(self) -> str:
        return """package com.example;

import org.junit.jupiter.api.Test;

public class StringSanitizerBehaviorTest {
    @Test
    void testBasic() {
        StringSanitizer sanitizer = new StringSanitizer();
        sanitizer.normalize("  Hello   WORLD  ");
        sanitizer.normalize("");
        sanitizer.normalize(null);
    }
}
"""

    def _repaired_string_test_source(self) -> str:
        return """package com.example;

import org.junit.jupiter.api.Test;

import org.junit.Assert;

public class StringSanitizerBehaviorTest {
    private static final String MIXED_CASE_WITH_EXTRA_SPACES = "  Hello   WORLD  ";
    private static final String NORMALIZED_GREETING = "hello world";
    private static final String EMPTY_INPUT = "";
    private static final String EMPTY_OUTPUT = "";

    @Test
    void testNormalizeTrimsLowercasesAndCollapsesWhitespace() {
        StringSanitizer sanitizer = new StringSanitizer();
        Assert.assertEquals("normalize should trim, lowercase, and collapse internal whitespace",
                NORMALIZED_GREETING, sanitizer.normalize(MIXED_CASE_WITH_EXTRA_SPACES));
    }

    @Test
    void testNormalizePreservesEmptyInput() {
        StringSanitizer sanitizer = new StringSanitizer();
        Assert.assertEquals("normalize should keep empty input empty",
                EMPTY_OUTPUT, sanitizer.normalize(EMPTY_INPUT));
    }

    @Test
    void testNormalizeRejectsNullInput() {
        StringSanitizer sanitizer = new StringSanitizer();
        Assert.assertTrue("normalize should reject null input",
                normalizeNullThrowsNullPointerException(sanitizer));
    }

    private boolean normalizeNullThrowsNullPointerException(StringSanitizer sanitizer) {
        try {
            sanitizer.normalize(null);
            return false;
        } catch (NullPointerException expected) {
            return true;
        }
    }
}
"""
