from __future__ import annotations

from .models import EvaluationDecision, ExecutionResult, ProjectTask, SmellReport


class MasterEvaluator:
    """Apply project success criteria to execution and smell reports."""

    def evaluate(
        self,
        task: ProjectTask,
        execution: ExecutionResult,
        smell_report: SmellReport,
    ) -> EvaluationDecision:
        reasons: list[str] = []
        feedback_items: list[str] = []
        authoritative_smell_count = (
            smell_report.count_from("AromaDr")
            if smell_report.aroma_dr_available
            else smell_report.count
        )
        criteria = {
            "compiled": execution.compiled,
            "passed": execution.passed,
            "smell_threshold": authoritative_smell_count <= task.max_accepted_smells,
        }

        if not execution.compiled:
            reasons.append("Generated tests did not compile.")
            feedback_items.append("Fix Java compilation errors before changing test intent.")

        if execution.compiled and not execution.passed:
            reasons.append("Generated tests compiled but failed.")
            feedback_items.append("Keep valid expected behavior, but repair failing assertions or setup.")

        if authoritative_smell_count > task.max_accepted_smells:
            detector_name = "AromaDr" if smell_report.aroma_dr_available else "combined"
            reasons.append(
                f"Detected {authoritative_smell_count} authoritative "
                f"{detector_name} test smell(s)."
            )
            feedback_items.extend(self._feedback_from_smells(smell_report))

        accepted = all(criteria.values())
        if accepted:
            reasons.append(
                "Tests compile, pass, and no authoritative smell findings remain."
            )
            feedback_items.append("No repair needed.")

        return EvaluationDecision(
            accepted=accepted,
            reasons=reasons,
            feedback_items=feedback_items,
            criteria=criteria,
        )

    def _feedback_from_smells(self, smell_report: SmellReport) -> list[str]:
        templates = {
            "AssertionRoulette": "For each test with multiple assertions, either split it into focused one-assertion tests or use assertion calls with an explicit message that AromaDr can read.",
            "ExceptionHandling": "Move try/catch logic into a non-test helper and assert the helper result from the test method so the test body stays focused.",
            "MagicNumberTest": "Replace numeric literals inside assertion arguments with named constants such as EXPECTED_SUM, DIVIDEND, or MAX_BOUND.",
            "UnknownTest": "Ensure the test contains an AromaDr-recognized assertion such as Assert.assertEquals, Assert.assertTrue, or Assert.fail; avoid relying only on assertThrows.",
            "GenericTestName": "Rename generic test methods to describe behavior and expected outcome.",
            "MissingAssertion": "Add explicit assertions for return values, state changes, or thrown exceptions.",
            "MissingExceptionCase": "Add a negative test for divide-by-zero behavior using an exception assertion.",
            "OverlyBroadTest": "Split broad tests into one focused test method per behavior.",
            "ExcessiveMocking": "Replace unnecessary mocks with real collaborators when the dependency is local and deterministic.",
        }
        items: list[str] = []
        seen: set[str] = set()
        findings = (
            smell_report.findings_from("AromaDr")
            if smell_report.aroma_dr_available
            else smell_report.findings
        )
        for finding in findings:
            text = templates.get(finding.smell_type, finding.message)
            if text not in seen:
                items.append(text)
                seen.add(text)
        return items


class FeedbackGenerator:
    """Convert master decisions into a repair prompt for the coding agent."""

    def build_feedback(self, decision: EvaluationDecision, smell_report: SmellReport) -> str:
        lines = ["Repair the existing Java test file using these findings:"]
        for item in decision.feedback_items:
            lines.append(f"- {item}")
        if smell_report.findings:
            lines.append("")
            lines.append("Detected smell locations:")
            for finding in smell_report.findings:
                lines.append(
                    f"- {finding.smell_type} at {finding.file.name}:{finding.line}: {finding.message}"
                )
        return "\n".join(lines)
