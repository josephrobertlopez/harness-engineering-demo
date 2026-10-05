"""Coverage tests for the L6 debate layer."""

from pathlib import Path
from specgate.l6_debate import (
    _build_judge_prompt,
    _build_prover_prompt,
    _build_refuter_prompt,
    _run_judge,
    run_debate,
)
from unittest.mock import Mock, patch
from unittest.mock import Mock, patch
import json
import subprocess
import tempfile
import unittest


class TestBuildPrompts(unittest.TestCase):
    """Test prompt building functions."""

    # covers: AC-7
    def test_build_prover_prompt(self) -> None:
        """Test building prover prompt."""
        inputs = {"change": "Added new feature"}
        prompt = _build_prover_prompt(inputs)

        self.assertIsInstance(prompt, str)
        self.assertIn("prover", prompt)
        self.assertIn("Added new feature", prompt)

    # covers: AC-7
    def test_build_refuter_prompt(self) -> None:
        """Test building refuter prompt."""
        inputs = {"change": "Added new feature"}
        prompt = _build_refuter_prompt(inputs)

        self.assertIsInstance(prompt, str)
        self.assertIn("refuter", prompt)
        self.assertIn("Added new feature", prompt)

    # covers: AC-7
    def test_build_judge_prompt(self) -> None:
        """Test building judge prompt."""
        prover = {"verdict": "pass"}
        refuter = {"verdict": "veto"}
        prompt = _build_judge_prompt(0, prover, refuter)

        self.assertIsInstance(prompt, str)
        self.assertIn("judge", prompt)
        self.assertIn("0", prompt)

    # covers: AC-7
    def test_build_prover_prompt_empty_change(self) -> None:
        """Test building prover prompt with no change."""
        inputs: dict[str, str] = {}
        prompt = _build_prover_prompt(inputs)

        self.assertIsInstance(prompt, str)
        self.assertIn("prover", prompt)

    # covers: AC-7
    def test_build_refuter_prompt_empty_change(self) -> None:
        """Test building refuter prompt with no change."""
        inputs: dict[str, str] = {}
        prompt = _build_refuter_prompt(inputs)

        self.assertIsInstance(prompt, str)
        self.assertIn("refuter", prompt)


class TestRunJudge(unittest.TestCase):
    """Test _run_judge function."""

    # covers: AC-7
    def test_run_judge_cache_hit(self) -> None:
        """Test _run_judge with cache hit."""
        prompt = "test prompt"
        model = "test-model"
        cache_data = {
            "abc123": {"verdict": {"verdict": "pass"}}
        }
        cache_file = Path("/tmp/test.json")

        with patch('hashlib.sha256') as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "abc123"

            verdict, calls, error = _run_judge(
                "claude",
                prompt,
                model,
                cache_data,
                cache_file,
                {},
            )

            self.assertEqual(calls, 0)
            self.assertIsNone(error)
            self.assertEqual(verdict, {"verdict": "pass"})

    # covers: AC-7
    def test_run_judge_cache_miss_no_token(self) -> None:
        """Test _run_judge with cache miss and no token."""
        prompt = "test prompt"
        model = "test-model"
        cache_data: dict[str, dict[str, dict[str, str]]] = {}
        cache_file = Path("/tmp/test.json")
        env: dict[str, str] = {}

        verdict, calls, error = _run_judge(
            "claude",
            prompt,
            model,
            cache_data,
            cache_file,
            env,
        )

        self.assertEqual(calls, 0)
        self.assertEqual(error, "SG602")
        self.assertIsNone(verdict)

    # covers: AC-7
    def test_run_judge_timeout(self) -> None:
        """Test _run_judge subprocess timeout."""
        prompt = "test prompt"
        model = "test-model"
        cache_data: dict[str, dict[str, dict[str, str]]] = {}
        cache_file = Path("/tmp/test.json")
        env = {"ANTHROPIC_API_KEY": "fake-key"}

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)

            verdict, calls, error = _run_judge(
                "claude",
                prompt,
                model,
                cache_data,
                cache_file,
                env,
            )

            self.assertEqual(calls, 1)
            self.assertEqual(error, "SG601")
            self.assertIsNone(verdict)

    # covers: AC-7
    def test_run_judge_subprocess_oserror(self) -> None:
        """Test _run_judge subprocess OSError."""
        prompt = "test prompt"
        model = "test-model"
        cache_data: dict[str, dict[str, dict[str, str]]] = {}
        cache_file = Path("/tmp/test.json")
        env = {"ANTHROPIC_API_KEY": "fake-key"}

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = OSError("command not found")

            verdict, calls, error = _run_judge(
                "claude",
                prompt,
                model,
                cache_data,
                cache_file,
                env,
            )

            self.assertEqual(calls, 1)
            self.assertEqual(error, "SG601")
            self.assertIsNone(verdict)

    # covers: AC-7
    def test_run_judge_invalid_json_envelope(self) -> None:
        """Test _run_judge with invalid JSON envelope."""
        prompt = "test prompt"
        model = "test-model"
        cache_data: dict[str, dict[str, dict[str, str]]] = {}
        cache_file = Path("/tmp/test.json")
        env = {"ANTHROPIC_API_KEY": "fake-key"}

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.stdout = "not valid json"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            verdict, calls, error = _run_judge(
                "claude",
                prompt,
                model,
                cache_data,
                cache_file,
                env,
            )

            self.assertEqual(calls, 1)
            self.assertEqual(error, "SG601")
            self.assertIsNone(verdict)

    # covers: AC-7
    def test_run_judge_non_end_turn_stop_reason(self) -> None:
        """Test _run_judge with non-end_turn stop_reason."""
        prompt = "test prompt"
        model = "test-model"
        cache_data: dict[str, dict[str, dict[str, str]]] = {}
        cache_file = Path("/tmp/test.json")
        env = {"ANTHROPIC_API_KEY": "fake-key"}

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            envelope = {"stop_reason": "max_tokens", "result": '{"verdict": "pass"}'}
            mock_result.stdout = json.dumps(envelope)
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            verdict, calls, error = _run_judge(
                "claude",
                prompt,
                model,
                cache_data,
                cache_file,
                env,
            )

            self.assertEqual(calls, 1)
            self.assertEqual(error, "SG601")
            self.assertIsNone(verdict)

    # covers: AC-7
    def test_run_judge_invalid_result_json(self) -> None:
        """Test _run_judge with invalid JSON in result field."""
        prompt = "test prompt"
        model = "test-model"
        cache_data: dict[str, dict[str, dict[str, str]]] = {}
        cache_file = Path("/tmp/test.json")
        env = {"ANTHROPIC_API_KEY": "fake-key"}

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            envelope = {"stop_reason": "end_turn", "result": "not json"}
            mock_result.stdout = json.dumps(envelope)
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            verdict, calls, error = _run_judge(
                "claude",
                prompt,
                model,
                cache_data,
                cache_file,
                env,
            )

            self.assertEqual(calls, 1)
            self.assertEqual(error, "SG601")
            self.assertIsNone(verdict)

    # covers: AC-7
    def test_run_judge_success_with_caching(self) -> None:
        """Test _run_judge success and caching."""
        prompt = "test prompt"
        model = "test-model"
        cache_data: dict[str, dict[str, dict[str, str]]] = {}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = Path(f.name)

        try:
            env = {"ANTHROPIC_API_KEY": "fake-key"}

            with patch('subprocess.run') as mock_run:
                mock_result = Mock()
                verdict_obj = {"verdict": "pass", "file": "", "line": "", "claim": ""}
                envelope = {
                    "stop_reason": "end_turn",
                    "result": json.dumps(verdict_obj)
                }
                mock_result.stdout = json.dumps(envelope)
                mock_result.returncode = 0
                mock_run.return_value = mock_result

                verdict, calls, error = _run_judge(
                    "claude",
                    prompt,
                    model,
                    cache_data,
                    cache_file,
                    env,
                )

                self.assertEqual(calls, 1)
                self.assertIsNone(error)
                self.assertEqual(verdict, verdict_obj)
        finally:
            if cache_file.exists():
                cache_file.unlink()


class TestRunDebate(unittest.TestCase):
    """Test run_debate function."""

    # covers: AC-7
    def test_run_debate_basic(self) -> None:
        """Test run_debate basic functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            inputs = {"change": "test change"}

            def mock_recheck(file: str, line: str, claim: str) -> bool:
                return False

            result = run_debate(change_dir, inputs, mock_recheck, claude_bin="false")

            self.assertIsInstance(result, dict)
            self.assertIn("findings", result)
            self.assertIn("ignored_vetoes", result)
            self.assertIn("calls", result)
            self.assertIsInstance(result["findings"], list)
            self.assertIsInstance(result["ignored_vetoes"], list)

    # covers: AC-7
    def test_run_debate_with_env(self) -> None:
        """Test run_debate with custom environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            inputs = {"change": "test change"}
            env = {"ANTHROPIC_API_KEY": "fake-key"}

            def mock_recheck(file: str, line: str, claim: str) -> bool:
                return False

            result = run_debate(
                change_dir, inputs, mock_recheck, claude_bin="false", env=env
            )

            self.assertIsInstance(result, dict)
            self.assertIn("findings", result)

    # covers: AC-7
    def test_run_debate_sg602_no_token(self) -> None:
        """Test run_debate produces SG602 when no token."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            inputs = {"change": "test change"}
            env: dict[str, str] = {}

            def mock_recheck(file: str, line: str, claim: str) -> bool:
                return False

            result = run_debate(
                change_dir, inputs, mock_recheck, claude_bin="false", env=env
            )

            self.assertGreater(len(result["findings"]), 0)
            self.assertTrue(
                any(f["rule"] == "SG602" for f in result["findings"])
            )


class TestIntegration(unittest.TestCase):
    """Integration tests for L6 debate layer."""

    # covers: AC-7
    def test_sg602_rule_implementation(self) -> None:
        """Test SG602 rule is properly implemented."""
        prompt = "test"
        model = "test"
        cache_data: dict[str, dict[str, dict[str, str]]] = {}
        cache_file = Path("/tmp/test.json")
        env: dict[str, str] = {}

        _, _, error = _run_judge("claude", prompt, model, cache_data, cache_file, env)

        self.assertEqual(error, "SG602")


class TestBuildPromptsBranches(unittest.TestCase):
    """Test additional branch coverage for prompt builders."""

    # covers: AC-7
    def test_build_prover_prompt_with_multiline_change(self) -> None:
        """Test building prover prompt with multiline change."""
        inputs = {"change": "Line 1\nLine 2\nLine 3"}
        prompt = _build_prover_prompt(inputs)
        self.assertIn("Line 1", prompt)
        self.assertIn("Line 2", prompt)
        self.assertIn("Line 3", prompt)

    # covers: AC-7
    def test_build_refuter_prompt_with_special_chars(self) -> None:
        """Test building refuter prompt with special characters."""
        inputs = {"change": 'Change "with" quotes and \'apostrophes\''}
        prompt = _build_refuter_prompt(inputs)
        self.assertIsInstance(prompt, str)
        self.assertIn("refuter", prompt)

    # covers: AC-7
    def test_build_judge_prompt_different_judges(self) -> None:
        """Test building judge prompts for different judge IDs."""
        prover = {"verdict": "pass"}
        refuter = {"verdict": "veto"}

        for judge_id in [0, 1, 2]:
            prompt = _build_judge_prompt(judge_id, prover, refuter)
            self.assertIn(str(judge_id), prompt)

    # covers: AC-7
    def test_build_judge_prompt_with_complex_verdict(self) -> None:
        """Test building judge prompt with complex verdict objects."""
        prover = {"verdict": "pass", "file": "test.py", "line": 10, "claim": "good"}
        refuter = {"verdict": "veto", "file": "src.py", "line": 20, "claim": "bad"}
        prompt = _build_judge_prompt(0, prover, refuter)

        self.assertIn("pass", prompt)
        self.assertIn("veto", prompt)
        self.assertIn("test.py", prompt)
        self.assertIn("src.py", prompt)


class TestRunJudgeBranches(unittest.TestCase):
    """Test additional branch coverage for _run_judge."""

    # covers: AC-7
    def test_run_judge_cache_hit_with_verdict_data(self) -> None:
        """Test _run_judge retrieves correct verdict from cache."""
        prompt = "test prompt"
        model = "test-model"
        cached_verdict = {"verdict": "veto", "file": "test.py", "line": 5, "claim": "broken"}
        cache_data = {}
        cache_file = Path("/tmp/test.json")

        with patch('hashlib.sha256') as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "test_key"
            cache_data["test_key"] = {"verdict": cached_verdict}

            verdict, calls, error = _run_judge(
                "claude", prompt, model, cache_data, cache_file, {}
            )

            self.assertEqual(verdict, cached_verdict)
            self.assertEqual(calls, 0)
            self.assertIsNone(error)

    # covers: AC-7
    def test_run_judge_with_anthropic_api_key(self) -> None:
        """Test _run_judge detects ANTHROPIC_API_KEY."""
        prompt = "test"
        model = "test"
        cache_data = {}
        cache_file = Path("/tmp/test.json")
        env = {"ANTHROPIC_API_KEY": "sk-test"}

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = OSError("no claude")

            verdict, calls, error = _run_judge(
                "claude", prompt, model, cache_data, cache_file, env
            )

            self.assertEqual(error, "SG601")
            self.assertEqual(calls, 1)

    # covers: AC-7
    def test_run_judge_with_claude_code_oauth_token(self) -> None:
        """Test _run_judge detects CLAUDE_CODE_OAUTH_TOKEN."""
        prompt = "test"
        model = "test"
        cache_data = {}
        cache_file = Path("/tmp/test.json")
        env = {"CLAUDE_CODE_OAUTH_TOKEN": "oauth-test"}

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)

            verdict, calls, error = _run_judge(
                "claude", prompt, model, cache_data, cache_file, env
            )

            self.assertEqual(error, "SG601")
            self.assertEqual(calls, 1)

    # covers: AC-7
    def test_run_judge_successful_subprocess_run(self) -> None:
        """Test _run_judge handles successful subprocess.run."""
        prompt = "test prompt"
        model = "test-model"
        cache_data = {}
        cache_file = Path("/tmp/test.json")
        env = {"ANTHROPIC_API_KEY": "fake-key"}

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            verdict_obj = {"verdict": "pass", "file": "", "line": "", "claim": ""}
            envelope = {
                "stop_reason": "end_turn",
                "result": json.dumps(verdict_obj)
            }
            mock_result.stdout = json.dumps(envelope)
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            verdict, calls, error = _run_judge(
                "claude", prompt, model, cache_data, cache_file, env
            )

            self.assertEqual(verdict, verdict_obj)
            self.assertEqual(calls, 1)
            self.assertIsNone(error)

    # covers: AC-7
    def test_run_judge_cache_write_failure(self) -> None:
        """Test _run_judge handles cache write failure gracefully."""
        prompt = "test prompt"
        model = "test-model"
        cache_data = {}
        cache_file = Path("/tmp/nonexistent/dir/cache.json")
        env = {"ANTHROPIC_API_KEY": "fake-key"}

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            verdict_obj = {"verdict": "pass"}
            envelope = {
                "stop_reason": "end_turn",
                "result": json.dumps(verdict_obj)
            }
            mock_result.stdout = json.dumps(envelope)
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Even if cache file write fails, should return success
            verdict, calls, error = _run_judge(
                "claude", prompt, model, cache_data, cache_file, env
            )

            self.assertEqual(verdict, verdict_obj)
            self.assertIsNone(error)

    # covers: AC-7
    def test_run_judge_json_decode_error_envelope(self) -> None:
        """Test _run_judge with JSON decode error in envelope."""
        prompt = "test"
        model = "test"
        cache_data = {}
        cache_file = Path("/tmp/test.json")
        env = {"ANTHROPIC_API_KEY": "fake"}

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.stdout = "not json {incomplete"
            mock_run.return_value = mock_result

            verdict, calls, error = _run_judge(
                "claude", prompt, model, cache_data, cache_file, env
            )

            self.assertEqual(error, "SG601")
            self.assertIsNone(verdict)

    # covers: AC-7
    def test_run_judge_json_value_error_envelope(self) -> None:
        """Test _run_judge with ValueError in JSON envelope parsing."""
        prompt = "test"
        model = "test"
        cache_data = {}
        cache_file = Path("/tmp/test.json")
        env = {"ANTHROPIC_API_KEY": "fake"}

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(stdout='{"invalid": NaN}')

            with patch('json.loads') as mock_json:
                mock_json.side_effect = ValueError("invalid json")
                verdict, calls, error = _run_judge(
                    "claude", prompt, model, cache_data, cache_file, env
                )

                self.assertEqual(error, "SG601")

    # covers: AC-7
    def test_run_judge_json_value_error_result(self) -> None:
        """Test _run_judge with ValueError parsing result JSON."""
        prompt = "test"
        model = "test"
        cache_data = {}
        cache_file = Path("/tmp/test.json")
        env = {"ANTHROPIC_API_KEY": "fake"}

        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            envelope = {
                "stop_reason": "end_turn",
                "result": "not valid json"
            }
            mock_result.stdout = json.dumps(envelope)
            mock_run.return_value = mock_result

            verdict, calls, error = _run_judge(
                "claude", prompt, model, cache_data, cache_file, env
            )

            self.assertEqual(error, "SG601")
            self.assertIsNone(verdict)


class TestRunDebateBranches(unittest.TestCase):
    """Test additional branch coverage for run_debate."""

    # covers: AC-7
    def test_run_debate_prover_error(self) -> None:
        """Test run_debate handles prover error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            inputs = {"change": "test"}

            with patch('specgate.l6_debate._run_judge') as mock_judge:
                mock_judge.side_effect = [
                    (None, 1, "SG602"),  # Prover error
                ]

                def mock_recheck(_f: str, _l: str, _c: str) -> bool:
                    return False

                result = run_debate(change_dir, inputs, mock_recheck)

                self.assertTrue(any(f["rule"] == "SG602" for f in result["findings"]))

    # covers: AC-7
    def test_run_debate_prover_output_invalid(self) -> None:
        """Test run_debate with invalid prover output (None with no error)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            inputs = {"change": "test"}

            with patch('specgate.l6_debate._run_judge') as mock_judge:
                mock_judge.side_effect = [
                    (None, 1, None),  # Prover returns None with no error
                ]

                def mock_recheck(_f: str, _l: str, _c: str) -> bool:
                    return False

                result = run_debate(change_dir, inputs, mock_recheck)

                self.assertTrue(any(f["rule"] == "SG601" for f in result["findings"]))

    # covers: AC-7
    def test_run_debate_refuter_error(self) -> None:
        """Test run_debate handles refuter error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            inputs = {"change": "test"}

            with patch('specgate.l6_debate._run_judge') as mock_judge:
                mock_judge.side_effect = [
                    ({"verdict": "pass"}, 1, None),  # Prover OK
                    (None, 1, "SG602"),  # Refuter error
                ]

                def mock_recheck(_f: str, _l: str, _c: str) -> bool:
                    return False

                result = run_debate(change_dir, inputs, mock_recheck)

                self.assertTrue(any(f["rule"] == "SG602" for f in result["findings"]))

    # covers: AC-7
    def test_run_debate_refuter_output_invalid(self) -> None:
        """Test run_debate with invalid refuter output (None with no error)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            inputs = {"change": "test"}

            with patch('specgate.l6_debate._run_judge') as mock_judge:
                mock_judge.side_effect = [
                    ({"verdict": "pass"}, 1, None),  # Prover OK
                    (None, 1, None),  # Refuter returns None with no error
                ]

                def mock_recheck(_f: str, _l: str, _c: str) -> bool:
                    return False

                result = run_debate(change_dir, inputs, mock_recheck)

                self.assertTrue(any(f["rule"] == "SG601" for f in result["findings"]))

    # covers: AC-7
    def test_run_debate_judge_error(self) -> None:
        """Test run_debate handles judge error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            inputs = {"change": "test"}

            with patch('specgate.l6_debate._run_judge') as mock_judge:
                mock_judge.side_effect = [
                    ({"verdict": "pass"}, 1, None),  # Prover OK
                    ({"verdict": "veto"}, 1, None),  # Refuter OK
                    (None, 1, "SG602"),  # Judge 0 error
                ]

                def mock_recheck(_f: str, _l: str, _c: str) -> bool:
                    return False

                result = run_debate(change_dir, inputs, mock_recheck)

                self.assertTrue(any(f["rule"] == "SG602" for f in result["findings"]))

    # covers: AC-7
    def test_run_debate_majority_veto_confirmed(self) -> None:
        """Test run_debate with confirmed majority veto."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            inputs = {"change": "test"}

            with patch('specgate.l6_debate._run_judge') as mock_judge:
                veto_obj = {
                    "verdict": "veto",
                    "file": "src.py",
                    "line": "10",
                    "claim": "broken"
                }
                mock_judge.side_effect = [
                    ({"verdict": "pass"}, 1, None),
                    ({"verdict": "veto"}, 1, None),
                    (veto_obj, 1, None),  # Judge 0
                    (veto_obj, 1, None),  # Judge 1
                    ({"verdict": "pass"}, 1, None),  # Judge 2
                ]

                def mock_recheck(_f: str, _l: str, _c: str) -> bool:
                    return True  # Confirm the veto

                result = run_debate(change_dir, inputs, mock_recheck)

                self.assertTrue(any(f["rule"] == "SG603" for f in result["findings"]))

    # covers: AC-7
    def test_run_debate_majority_veto_unconfirmed(self) -> None:
        """Test run_debate with unconfirmed majority veto."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            inputs = {"change": "test"}

            with patch('specgate.l6_debate._run_judge') as mock_judge:
                veto_obj = {
                    "verdict": "veto",
                    "file": "src.py",
                    "line": "10",
                    "claim": "broken"
                }
                mock_judge.side_effect = [
                    ({"verdict": "pass"}, 1, None),
                    ({"verdict": "veto"}, 1, None),
                    (veto_obj, 1, None),
                    (veto_obj, 1, None),
                    ({"verdict": "pass"}, 1, None),
                ]

                def mock_recheck(_f: str, _l: str, _c: str) -> bool:
                    return False  # Veto unconfirmed

                result = run_debate(change_dir, inputs, mock_recheck)

                self.assertTrue(len(result["ignored_vetoes"]) > 0)

    # covers: AC-7
    def test_run_debate_single_judge_veto(self) -> None:
        """Test run_debate with single judge veto (not majority)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            inputs = {"change": "test"}

            with patch('specgate.l6_debate._run_judge') as mock_judge:
                veto_obj = {
                    "verdict": "veto",
                    "file": "src.py",
                    "line": "10",
                    "claim": "broken"
                }
                mock_judge.side_effect = [
                    ({"verdict": "pass"}, 1, None),
                    ({"verdict": "veto"}, 1, None),
                    (veto_obj, 1, None),  # Judge 0 veto
                    ({"verdict": "pass"}, 1, None),  # Judge 1 pass
                    ({"verdict": "pass"}, 1, None),  # Judge 2 pass
                ]

                def mock_recheck(_f: str, _l: str, _c: str) -> bool:
                    return False

                result = run_debate(change_dir, inputs, mock_recheck)

                # Single veto should be ignored
                self.assertTrue(len(result["ignored_vetoes"]) > 0)
                # Verify it's recorded as single judge veto
                self.assertTrue(any("Single judge veto" in v.get("reason", "") for v in result["ignored_vetoes"]))

    # covers: AC-7
    def test_run_debate_single_judge_veto_with_details_single_veto(self) -> None:
        """Test run_debate with exactly one judge veto and proper details."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            inputs = {"change": "test change"}

            with patch('specgate.l6_debate._run_judge') as mock_judge:
                veto = {"verdict": "veto", "file": "test.py", "line": "5", "claim": "issue"}
                pass_obj = {"verdict": "pass", "file": "", "line": "", "claim": ""}

                # Prover pass, Refuter veto (1 veto), Judge 0 veto (now 2 vetoes, majority)
                # Actually we need exactly veto_count == 1, so refuter shouldn't veto if judges will
                # Let me set it up: Prover pass, Refuter pass, Judge 0 veto (1), Judge 1 pass, Judge 2 pass
                mock_judge.side_effect = [
                    (pass_obj, 1, None),  # Prover
                    (pass_obj, 1, None),  # Refuter
                    (veto, 1, None),      # Judge 0 - first veto, veto_count becomes 1
                    (pass_obj, 1, None),  # Judge 1 - pass
                    (pass_obj, 1, None),  # Judge 2 - pass
                ]

                def mock_recheck(_f: str, _l: str, _c: str) -> bool:
                    return False

                result = run_debate(change_dir, inputs, mock_recheck)

                # With veto_count == 1, should go to elif branch and append to ignored_vetoes
                self.assertTrue(len(result["ignored_vetoes"]) > 0)
                veto_item = result["ignored_vetoes"][0]
                self.assertEqual(veto_item["file"], "test.py")
                self.assertEqual(veto_item["line"], "5")
                self.assertEqual(veto_item["claim"], "issue")

    # covers: AC-7
    def test_run_debate_no_veto(self) -> None:
        """Test run_debate with no vetoes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            inputs = {"change": "test"}

            with patch('specgate.l6_debate._run_judge') as mock_judge:
                pass_obj = {"verdict": "pass", "file": "", "line": "", "claim": ""}
                mock_judge.side_effect = [
                    (pass_obj, 1, None),
                    (pass_obj, 1, None),
                    (pass_obj, 1, None),
                    (pass_obj, 1, None),
                    (pass_obj, 1, None),
                ]

                def mock_recheck(_f: str, _l: str, _c: str) -> bool:
                    return False

                result = run_debate(change_dir, inputs, mock_recheck)

                # No SG603 findings
                self.assertFalse(any(f["rule"] == "SG603" for f in result["findings"]))

    # covers: AC-7
    def test_run_debate_cache_directory_creation(self) -> None:
        """Test run_debate creates cache directory if needed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir) / "nested" / "dir"

            def mock_recheck(_f: str, _l: str, _c: str) -> bool:
                return False

            result = run_debate(change_dir, {}, mock_recheck, claude_bin="false")

            # Directory should be created
            self.assertTrue(change_dir.exists())

    # covers: AC-7
    def test_run_debate_cache_file_corruption(self) -> None:
        """Test run_debate handles corrupted cache file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            cache_file = change_dir / "debate.cache.json"
            cache_file.write_text("corrupted json {[}]")

            def mock_recheck(_f: str, _l: str, _c: str) -> bool:
                return False

            result = run_debate(change_dir, {"change": "test"}, mock_recheck)

            # Should handle corruption gracefully
            self.assertIsInstance(result, dict)

    # covers: AC-7
    def test_run_debate_verdict_without_veto_details(self) -> None:
        """Test run_debate when veto_count >= 2 but veto_details is None."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            inputs = {"change": "test"}

            with patch('specgate.l6_debate._run_judge') as mock_judge:
                mock_judge.side_effect = [
                    ({"verdict": "pass"}, 1, None),
                    ({"verdict": "veto"}, 1, None),
                    (None, 1, None),  # Judge 0 returns None (invalid)
                    (None, 1, None),  # Judge 1 returns None (invalid)
                    ({"verdict": "pass"}, 1, None),  # Judge 2
                ]

                def mock_recheck(_f: str, _l: str, _c: str) -> bool:
                    return False

                result = run_debate(change_dir, inputs, mock_recheck)

                # Should handle None judge results
                self.assertIsInstance(result, dict)

    # covers: AC-7
    def test_run_debate_calls_counter(self) -> None:
        """Test run_debate counts subprocess calls correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            change_dir = Path(temp_dir)
            inputs = {"change": "test"}

            with patch('specgate.l6_debate._run_judge') as mock_judge:
                pass_obj = {"verdict": "pass"}
                mock_judge.side_effect = [
                    (pass_obj, 2, None),  # Prover: 2 calls
                    (pass_obj, 1, None),  # Refuter: 1 call
                    (pass_obj, 1, None),  # Judge 0: 1 call
                    (pass_obj, 1, None),  # Judge 1: 1 call
                    (pass_obj, 1, None),  # Judge 2: 1 call
                ]

                def mock_recheck(_f: str, _l: str, _c: str) -> bool:
                    return False

                result = run_debate(change_dir, inputs, mock_recheck)

                # Total calls: 2 + 1 + 1 + 1 + 1 = 6
                self.assertEqual(result["calls"], 6)
