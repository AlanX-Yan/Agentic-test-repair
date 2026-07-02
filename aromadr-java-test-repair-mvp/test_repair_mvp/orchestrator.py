from __future__ import annotations

from pathlib import Path

from .agents import TemplateCodingAgent
from .detectors import CompositeDetector
from .feedback import FeedbackGenerator, MasterEvaluator
from .harness import JavaExecutionHarness
from .models import IterationRecord, ProjectTask, RepairRun
from .reporting import ArtifactWriter


class GoalDrivenRepairOrchestrator:
    """Coordinate generate, execute, smell-detect, evaluate, and repair."""

    def __init__(self, artifacts_dir: Path) -> None:
        self.agent = TemplateCodingAgent()
        self.harness = JavaExecutionHarness()
        self.detector = CompositeDetector()
        self.evaluator = MasterEvaluator()
        self.feedback_generator = FeedbackGenerator()
        self.artifacts = ArtifactWriter(artifacts_dir)

    def run(self, task: ProjectTask) -> RepairRun:
        iterations: list[IterationRecord] = []
        self.agent.generate_initial_tests(task)

        for iteration in range(task.max_iterations + 1):
            execution = self.harness.run_tests(task)
            smell_report = self.detector.detect(task)
            decision = self.evaluator.evaluate(task, execution, smell_report)
            feedback = self.feedback_generator.build_feedback(decision, smell_report)
            record = IterationRecord(
                iteration=iteration,
                test_file=task.test_file,
                execution=execution,
                smell_report=smell_report,
                decision=decision,
                feedback=feedback,
            )
            iterations.append(record)
            self.artifacts.snapshot_iteration(record)

            if decision.accepted or iteration >= task.max_iterations:
                break

            self.agent.repair_tests(task, feedback, iteration + 1)

        run = RepairRun(
            task=task,
            iterations=iterations,
            final_accepted=iterations[-1].decision.accepted,
            artifacts_dir=self.artifacts.artifacts_dir,
        )
        self.artifacts.write_final_report(run)
        return run
