from __future__ import annotations

from .models import ProjectTask


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
