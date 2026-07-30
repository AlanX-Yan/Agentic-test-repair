import json
import os
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from test_repair_mvp.agents import (
    ApiBudget,
    BudgetExceededError,
    DeepSeekCodingAgent,
    DeepSeekConfig,
)
from test_repair_mvp.models import ProjectTask


class _FakeHttpResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class DeepSeekAgentTest(TestCase):
    def test_config_requires_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "DEEPSEEK_API_KEY"):
                DeepSeekConfig.from_env()

    def test_repairs_authorized_file_and_records_usage(self) -> None:
        with TemporaryDirectory() as temporary_dir:
            project = Path(temporary_dir)
            test_file = project / "src/test/java/com/example/ExampleTest.java"
            test_file.parent.mkdir(parents=True)
            original = (
                "package com.example;\n"
                "public class ExampleTest { int value() { return 1; } }\n"
            )
            replacement = (
                "package com.example;\n"
                "public class ExampleTest { int value() { return 2; } }\n"
            )
            test_file.write_text(original, encoding="utf-8")
            task = ProjectTask(
                task_id="test",
                project_root=project,
                source_under_test=project / "pom.xml",
                test_file=test_file,
                target_description="repair",
            )
            payload = {
                "id": "call-1",
                "model": "deepseek-v4-pro",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "replacement_source": replacement,
                                    "rationale": "focused repair",
                                    "addressed_smells": ["UnknownTest"],
                                    "assumptions": [],
                                }
                            )
                        },
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            }
            agent = DeepSeekCodingAgent(
                DeepSeekConfig(api_key="fake-secret"),
                project / "artifacts",
            )

            with patch(
                "urllib.request.urlopen",
                return_value=_FakeHttpResponse(payload),
            ) as urlopen:
                agent.repair_tests(task, "fix it", 1)

            self.assertEqual(replacement, test_file.read_text(encoding="utf-8"))
            request = urlopen.call_args.args[0]
            self.assertTrue(request.headers["Authorization"].startswith("Bearer "))
            records = json.loads(
                (project / "artifacts/model_calls.json").read_text(encoding="utf-8")
            )
            self.assertEqual(100, records[0]["usage"]["prompt_tokens"])
            self.assertNotIn(
                "fake-secret",
                (project / "artifacts/model_calls.json").read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                "fake-secret",
                (project / "artifacts/api_attempts.json").read_text(encoding="utf-8"),
            )

    def test_rejects_package_change_without_modifying_file(self) -> None:
        with TemporaryDirectory() as temporary_dir:
            project = Path(temporary_dir)
            test_file = project / "ExampleTest.java"
            original = "package one;\npublic class ExampleTest {}\n"
            test_file.write_text(original, encoding="utf-8")
            task = ProjectTask(
                task_id="test",
                project_root=project,
                source_under_test=project / "pom.xml",
                test_file=test_file,
                target_description="repair",
            )
            agent = DeepSeekCodingAgent(
                DeepSeekConfig(api_key="fake-secret"),
                project / "artifacts",
            )
            payload = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "replacement_source": (
                                        "package two;\npublic class ExampleTest {}\n"
                                    )
                                }
                            )
                        }
                    }
                ]
            }

            with patch(
                "urllib.request.urlopen",
                return_value=_FakeHttpResponse(payload),
            ):
                with self.assertRaisesRegex(ValueError, "package"):
                    agent.repair_tests(task, "fix it", 1)

            self.assertEqual(original, test_file.read_text(encoding="utf-8"))

    def test_budget_stops_request_before_http_call(self) -> None:
        with TemporaryDirectory() as temporary_dir:
            project = Path(temporary_dir)
            test_file = project / "ExampleTest.java"
            test_file.write_text("public class ExampleTest {}\n", encoding="utf-8")
            task = ProjectTask(
                task_id="test",
                project_root=project,
                source_under_test=project / "pom.xml",
                test_file=test_file,
                target_description="repair",
            )
            agent = DeepSeekCodingAgent(
                DeepSeekConfig(api_key="fake-secret"),
                project / "artifacts",
                budget=ApiBudget(limit_usd=0.000001),
            )

            with patch("urllib.request.urlopen") as urlopen:
                with self.assertRaises(BudgetExceededError):
                    agent.repair_tests(task, "fix it", 1)

            urlopen.assert_not_called()

    def test_cost_uses_cache_hit_and_miss_rates(self) -> None:
        with TemporaryDirectory() as temporary_dir:
            agent = DeepSeekCodingAgent(
                DeepSeekConfig(api_key="fake-secret"),
                Path(temporary_dir) / "artifacts",
            )
            cost = agent._usage_cost(
                {
                    "prompt_tokens": 1000,
                    "prompt_cache_hit_tokens": 800,
                    "prompt_cache_miss_tokens": 200,
                    "completion_tokens": 100,
                }
            )

        expected = 800 / 1_000_000 * 0.003625
        expected += 200 / 1_000_000 * 0.435
        expected += 100 / 1_000_000 * 0.87
        self.assertAlmostEqual(expected, cost)

    def test_transient_network_error_is_retried(self) -> None:
        with TemporaryDirectory() as temporary_dir:
            agent = DeepSeekCodingAgent(
                DeepSeekConfig(api_key="fake-secret"),
                Path(temporary_dir) / "artifacts",
            )
            payload = {"choices": [{"message": {"content": "{}"}}]}

            with patch(
                "urllib.request.urlopen",
                side_effect=[
                    urllib.error.URLError("temporary"),
                    _FakeHttpResponse(payload),
                ],
            ) as urlopen, patch("test_repair_mvp.agents.time.sleep"):
                response = agent._post_json({"messages": []})

            self.assertEqual(payload, response)
            self.assertEqual(2, urlopen.call_count)
